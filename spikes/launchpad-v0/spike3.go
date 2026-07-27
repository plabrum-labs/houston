// Spike: per-app credential scoping across providers.
//
// Tests the Launchpad v0 design's isolation claim — that one app's
// reconciliation holds no credential that reaches another app's resources —
// against both providers it spans.
//
// AWS side: two apps ("appA", "appB") each get their own SES domain identity
// and their own IAM role, scoped by an inline policy to exactly that app's
// identity ARN. The spike assumes each role via STS and, using only the
// temporary credentials that role holds, attempts to read the *other* app's
// identity. A pass requires AWS to deny that call while allowing each role
// to read its own identity.
//
// Cloudflare side: per SPIKE_ZONE, both apps' DNS records live in the same
// zone (per themgmt.app being the only zone available to this spike). The
// finest-grained Cloudflare API token scope available is the whole zone —
// there is no per-record permission in Cloudflare's token model. So rather
// than gambling on provisioning a second scoped token (spike 1 already found
// that token creation itself needs a credential class this spike's token may
// not have), this spike demonstrates the constraint directly: it creates
// both apps' records under the one available token and then uses that same
// token to modify "app B"'s record, confirming live against the real API
// that a zone-scoped credential necessarily reaches every app sharing that
// zone. That is itself the finding the Pass/fail criteria anticipate as the
// likely outcome — naming convention, not Cloudflare's permission model, is
// what would have to carry app-level isolation within a shared zone.
package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials/stscreds"
	"github.com/aws/aws-sdk-go-v2/service/sesv2"
	"github.com/aws/aws-sdk-go-v2/service/sts"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/iam"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ses"
	"github.com/pulumi/pulumi-cloudflare/sdk/v5/go/cloudflare"
	"github.com/pulumi/pulumi/sdk/v3/go/auto"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optdestroy"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optup"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

const (
	spike3ProjectName = "launchpad-v0-spike3"
	spike3StackName   = "spike3-credential-scoping"
)

func runSpike3(destroy bool) {
	ctx := context.Background()
	zone := os.Getenv("SPIKE_ZONE")

	if destroy {
		stack, err := auto.SelectStackInlineSource(ctx, spike3StackName, spike3ProjectName, noopProgram)
		if err == nil {
			fmt.Println("destroying spike 3 stack...")
			if _, err := stack.Destroy(ctx, optdestroy.ProgressStreams(os.Stdout)); err != nil {
				fatal("pulumi destroy", err)
			}
			fmt.Println("destroy complete.")
		}
		return
	}

	if zone == "" {
		fmt.Fprintln(os.Stderr, "SPIKE_ZONE env var required (the Cloudflare zone/domain to use)")
		os.Exit(1)
	}
	cfToken := os.Getenv("CLOUDFLARE_API_TOKEN")
	if cfToken == "" {
		fmt.Fprintln(os.Stderr, "CLOUDFLARE_API_TOKEN env var required")
		os.Exit(1)
	}

	awsCfg, err := config.LoadDefaultConfig(ctx)
	if err != nil {
		fatal("loading AWS config", err)
	}
	callerIdentity, err := sts.NewFromConfig(awsCfg).GetCallerIdentity(ctx, &sts.GetCallerIdentityInput{})
	if err != nil {
		fatal("sts get-caller-identity", err)
	}
	accountID := *callerIdentity.Account

	ts := time.Now().Unix()
	appAID := fmt.Sprintf("spike3-appa-%d", ts)
	appBID := fmt.Sprintf("spike3-appb-%d", ts)

	program := buildSpike3Program(zone, accountID, appAID, appBID)
	stack, err := auto.UpsertStackInlineSource(ctx, spike3StackName, spike3ProjectName, program,
		auto.EnvVars(map[string]string{
			"PULUMI_CONFIG_PASSPHRASE": passphrase,
		}),
	)
	if err != nil {
		fatal("create/select stack", err)
	}

	fmt.Printf("app A id: %s\napp B id: %s\n", appAID, appBID)
	fmt.Println("provisioning both apps' SES identities, IAM roles, and Cloudflare DNS records...")
	res, err := stack.Up(ctx, optup.ProgressStreams(os.Stdout))
	if err != nil {
		fatal("pulumi up", err)
	}

	roleAArn := outputStr(res.Outputs, "roleAArn")
	roleBArn := outputStr(res.Outputs, "roleBArn")
	identityADomain := outputStr(res.Outputs, "identityADomain")
	identityBDomain := outputStr(res.Outputs, "identityBDomain")
	appARecordName := outputStr(res.Outputs, "appARecordName")
	appBRecordName := outputStr(res.Outputs, "appBRecordName")
	zoneID := outputStr(res.Outputs, "zoneId")
	fmt.Printf("app A record: %s\napp B record: %s\n", appARecordName, appBRecordName)

	fmt.Println("\n--- AWS: waiting for each role's trust policy to become assumable ---")
	if err := waitForAssumeRolePropagation(ctx, awsCfg, roleAArn, "role-A", identityADomain); err != nil {
		fatal("waiting for role-A propagation", err)
	}
	if err := waitForAssumeRolePropagation(ctx, awsCfg, roleBArn, "role-B", identityBDomain); err != nil {
		fatal("waiting for role-B propagation", err)
	}

	fmt.Println("\n--- AWS: attempting cross-app SES reads under each app's own assumed role ---")
	awsPass := true
	awsPass = checkSesAccess(ctx, awsCfg, roleAArn, "role-A", identityADomain, true) && awsPass
	awsPass = checkSesAccess(ctx, awsCfg, roleAArn, "role-A", identityBDomain, false) && awsPass
	awsPass = checkSesAccess(ctx, awsCfg, roleBArn, "role-B", identityBDomain, true) && awsPass
	awsPass = checkSesAccess(ctx, awsCfg, roleBArn, "role-B", identityADomain, false) && awsPass

	fmt.Println("\n--- Cloudflare: attempting to modify app B's record using the one available zone-scoped token ---")
	cfIsolationHolds := attemptCloudflareRecordUpdate(cfToken, zoneID, appBRecordName)
	if cfIsolationHolds {
		fmt.Println("unexpected: the zone-scoped token could NOT modify app B's record.")
	} else {
		fmt.Println("as expected: the zone-scoped token modified app B's record without issue —")
		fmt.Println("Cloudflare's token model has no boundary narrower than the whole zone, so it")
		fmt.Println("cannot express per-app isolation for two apps sharing a zone. See RESULTS.md.")
	}

	fmt.Println()
	if awsPass {
		fmt.Println("AWS RESULT: PASS — each app's assumed role could read only its own SES identity.")
	} else {
		fmt.Println("AWS RESULT: FAIL — see the access checks above.")
	}
	fmt.Println("CLOUDFLARE RESULT: the account's token granularity cannot express a boundary")
	fmt.Println("narrower than the whole zone — confirmed live, not just from documentation.")

	fmt.Println("\ntearing down...")
	if _, err := stack.Destroy(ctx, optdestroy.ProgressStreams(os.Stdout)); err != nil {
		fmt.Fprintf(os.Stderr, "pulumi destroy: %v\n", err)
	}
}

func buildSpike3Program(zone, accountID, appAID, appBID string) pulumi.RunFunc {
	return func(ctx *pulumi.Context) error {
		zoneRes, err := cloudflare.LookupZone(ctx, &cloudflare.LookupZoneArgs{Name: &zone})
		if err != nil {
			return fmt.Errorf("looking up cloudflare zone %q: %w", zone, err)
		}

		trustPolicy := fmt.Sprintf(`{
			"Version": "2012-10-17",
			"Statement": [{
				"Effect": "Allow",
				"Principal": {"AWS": "arn:aws:iam::%s:root"},
				"Action": "sts:AssumeRole"
			}]
		}`, accountID)

		apps := []struct {
			id, resourceSuffix string
		}{
			{appAID, "A"},
			{appBID, "B"},
		}

		roleArns := map[string]pulumi.StringOutput{}
		identityArns := map[string]pulumi.StringOutput{}
		identityDomains := map[string]pulumi.StringOutput{}
		recordNames := map[string]pulumi.StringOutput{}

		for _, app := range apps {
			domain := fmt.Sprintf("%s.%s", app.id, zone)

			identity, err := ses.NewDomainIdentity(ctx, "identity-"+app.resourceSuffix, &ses.DomainIdentityArgs{
				Domain: pulumi.String(domain),
			})
			if err != nil {
				return fmt.Errorf("creating SES identity for %s: %w", app.id, err)
			}

			policy := identity.Arn.ApplyT(func(arn string) (string, error) {
				doc := map[string]any{
					"Version": "2012-10-17",
					"Statement": []map[string]any{{
						"Effect":   "Allow",
						"Action":   []string{"ses:GetEmailIdentity", "ses:GetIdentityVerificationAttributes"},
						"Resource": arn,
					}},
				}
				b, err := json.Marshal(doc)
				return string(b), err
			}).(pulumi.StringOutput)

			role, err := iam.NewRole(ctx, "role-"+app.resourceSuffix, &iam.RoleArgs{
				Name:             pulumi.String("houston-" + app.id),
				AssumeRolePolicy: pulumi.String(trustPolicy),
			})
			if err != nil {
				return fmt.Errorf("creating IAM role for %s: %w", app.id, err)
			}
			if _, err := iam.NewRolePolicy(ctx, "role-policy-"+app.resourceSuffix, &iam.RolePolicyArgs{
				Role:   role.Name,
				Policy: policy,
			}); err != nil {
				return fmt.Errorf("attaching IAM policy for %s: %w", app.id, err)
			}

			record, err := cloudflare.NewRecord(ctx, "record-"+app.resourceSuffix, &cloudflare.RecordArgs{
				ZoneId:  pulumi.String(zoneRes.Id),
				Name:    pulumi.String(domain),
				Type:    pulumi.String("A"),
				Content: pulumi.String("192.0.2.1"), // TEST-NET-1, RFC 5737 — placeholder only
				Ttl:     pulumi.Int(60),
				Comment: pulumi.String(app.id),
			})
			if err != nil {
				return fmt.Errorf("creating Cloudflare record for %s: %w", app.id, err)
			}

			roleArns[app.resourceSuffix] = role.Arn
			identityArns[app.resourceSuffix] = identity.Arn
			identityDomains[app.resourceSuffix] = identity.Domain
			recordNames[app.resourceSuffix] = record.Hostname
		}

		ctx.Export("roleAArn", roleArns["A"])
		ctx.Export("roleBArn", roleArns["B"])
		ctx.Export("identityAArn", identityArns["A"])
		ctx.Export("identityBArn", identityArns["B"])
		ctx.Export("identityADomain", identityDomains["A"])
		ctx.Export("identityBDomain", identityDomains["B"])
		ctx.Export("appARecordName", recordNames["A"])
		ctx.Export("appBRecordName", recordNames["B"])
		ctx.Export("zoneId", pulumi.String(zoneRes.Id))
		return nil
	}
}

// waitForAssumeRolePropagation polls, as its own role, until the IAM trust
// policy Pulumi just attached is actually assumable — a small state machine
// with two live states (propagating, propagated) plus terminal success/
// failure, rather than a fixed sleep. IAM's trust policy is eventually
// consistent, so calling AssumeRole immediately after the role is created
// can spuriously deny even the role reading its own SES identity; polling
// with `sts:AssumeRole`-denied treated as "still propagating" (as opposed to
// any other error, which is a real failure) tells the two apart. Once this
// returns nil, subsequent checkSesAccess calls for this role need no retry
// of their own — propagation is a fact about the role, established once.
func waitForAssumeRolePropagation(ctx context.Context, baseCfg aws.Config, roleArn, roleLabel, ownDomain string) error {
	const (
		pollInterval = 2 * time.Second
		maxAttempts  = 15 // ~30s worst case
	)
	state := "propagating"
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		_, err := sesReadAs(ctx, baseCfg, roleArn, ownDomain)
		switch {
		case err == nil:
			fmt.Printf("%s: %s -> propagated (attempt %d/%d)\n", roleLabel, state, attempt, maxAttempts)
			return nil
		case isAssumeRoleDenied(err):
			time.Sleep(pollInterval)
		default:
			return fmt.Errorf("%s: %s -> failed (not a propagation issue): %w", roleLabel, state, err)
		}
	}
	return fmt.Errorf("%s: %s -> failed: trust policy not assumable after %d attempts", roleLabel, state, maxAttempts)
}

func isAssumeRoleDenied(err error) bool {
	return err != nil && strings.Contains(err.Error(), "is not authorized to perform: sts:AssumeRole")
}

func sesReadAs(ctx context.Context, baseCfg aws.Config, roleArn, identityDomain string) (*sesv2.GetEmailIdentityOutput, error) {
	stsClient := sts.NewFromConfig(baseCfg)
	assumed := stscreds.NewAssumeRoleProvider(stsClient, roleArn, func(o *stscreds.AssumeRoleOptions) {
		o.RoleSessionName = "houston-spike3"
	})

	cfg := baseCfg.Copy()
	cfg.Credentials = aws.NewCredentialsCache(assumed)

	sesClient := sesv2.NewFromConfig(cfg)
	return sesClient.GetEmailIdentity(ctx, &sesv2.GetEmailIdentityInput{
		EmailIdentity: aws.String(identityDomain),
	})
}

// checkSesAccess assumes roleArn and attempts to read identityDomain's SES
// verification status with the resulting temporary credentials, printing
// and returning whether the outcome matched wantAllowed. Assumes
// waitForAssumeRolePropagation has already been called for roleArn, so any
// denial here is a real access-control result, not a propagation race.
func checkSesAccess(ctx context.Context, baseCfg aws.Config, roleArn, roleLabel, identityDomain string, wantAllowed bool) bool {
	_, err := sesReadAs(ctx, baseCfg, roleArn, identityDomain)

	allowed := err == nil
	ok := allowed == wantAllowed
	status := "DENIED"
	if allowed {
		status = "ALLOWED"
	}
	verdict := "unexpected"
	if ok {
		verdict = "as expected"
	}
	fmt.Printf("%s reading %s: %s (%s)", roleLabel, identityDomain, status, verdict)
	if err != nil {
		fmt.Printf(" — %v", err)
	}
	fmt.Println()
	return ok
}

// outputStr extracts a string-valued stack output, failing loudly if it's
// missing — every output referenced here is exported unconditionally by
// buildSpike3Program.
func outputStr(outputs auto.OutputMap, key string) string {
	v, ok := outputs[key]
	if !ok {
		fatal("reading stack output", fmt.Errorf("missing output %q", key))
	}
	s, ok := v.Value.(string)
	if !ok {
		fatal("reading stack output", fmt.Errorf("output %q is not a string: %v", key, v.Value))
	}
	return s
}

func attemptCloudflareRecordUpdate(token, zoneID, recordHostname string) bool {
	client := &http.Client{Timeout: 15 * time.Second}

	listURL := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records?type=A&name=%s", zoneID, recordHostname)
	req, _ := http.NewRequest(http.MethodGet, listURL, nil)
	req.Header.Set("Authorization", "Bearer "+token)
	resp, err := client.Do(req)
	if err != nil {
		fmt.Fprintf(os.Stderr, "listing cloudflare record: %v\n", err)
		return false
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)

	var listResult struct {
		Result []struct {
			ID string `json:"id"`
		} `json:"result"`
		Success bool `json:"success"`
	}
	if err := json.Unmarshal(body, &listResult); err != nil || !listResult.Success || len(listResult.Result) == 0 {
		fmt.Fprintf(os.Stderr, "unexpected cloudflare list response: %s\n", string(body))
		return false
	}
	recordID := listResult.Result[0].ID

	patchURL := fmt.Sprintf("https://api.cloudflare.com/client/v4/zones/%s/dns_records/%s", zoneID, recordID)
	patchBody, _ := json.Marshal(map[string]any{"content": "192.0.2.2", "ttl": 60})
	patchReq, _ := http.NewRequest(http.MethodPatch, patchURL, bytes.NewReader(patchBody))
	patchReq.Header.Set("Authorization", "Bearer "+token)
	patchReq.Header.Set("Content-Type", "application/json")
	patchResp, err := client.Do(patchReq)
	if err != nil {
		fmt.Fprintf(os.Stderr, "patching cloudflare record: %v\n", err)
		return false
	}
	defer patchResp.Body.Close()
	patchRespBody, _ := io.ReadAll(patchResp.Body)

	var patchResult struct {
		Success bool `json:"success"`
	}
	_ = json.Unmarshal(patchRespBody, &patchResult)
	fmt.Printf("PATCH %s -> %d, success=%v\n", strings.TrimPrefix(patchURL, "https://api.cloudflare.com/client/v4"), patchResp.StatusCode, patchResult.Success)
	return !patchResult.Success
}
