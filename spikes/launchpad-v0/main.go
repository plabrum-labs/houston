// Spike: cross-provider reconciliation, end to end.
//
// Tests the Launchpad v0 design's claim that one reconciliation can drive an
// app's infrastructure across both AWS and Cloudflare in a single pass: an
// ACM certificate and an SES domain identity are provisioned on AWS, each
// returning a DNS validation record as an output, and this same program
// creates the corresponding Cloudflare DNS record from that output — with no
// human copying a record between providers and no second `pulumi up`.
//
// Every taggable AWS resource carries houston:spike and houston:app-id tags;
// untaggable resources (the SES identity, the Cloudflare record) are named
// from the same app ID so they can be found by prefix at teardown time.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/acm"
	"github.com/pulumi/pulumi-aws/sdk/v6/go/aws/ses"
	"github.com/pulumi/pulumi-cloudflare/sdk/v5/go/cloudflare"
	"github.com/pulumi/pulumi/sdk/v3/go/auto"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optdestroy"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optup"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

const (
	projectName = "launchpad-v0-spike1"
	stackName   = "spike1-cross-provider-recon"
	spikeTag    = "launchpad-v0-cross-provider-reconciliation"
	passphrase  = "houston-spike-launchpad-v0"
)

func main() {
	destroy := flag.Bool("destroy", false, "tear down the spike stack instead of standing it up")
	flag.Parse()

	zone := os.Getenv("SPIKE_ZONE")
	if zone == "" {
		fmt.Fprintln(os.Stderr, "SPIKE_ZONE env var required (the Cloudflare zone/domain to use)")
		os.Exit(1)
	}
	if os.Getenv("CLOUDFLARE_API_TOKEN") == "" {
		fmt.Fprintln(os.Stderr, "CLOUDFLARE_API_TOKEN env var required")
		os.Exit(1)
	}

	// appID only names newly-created resources; destroy matches by the stack's
	// existing URNs (stable logical names below), so a fresh value here is fine.
	appID := fmt.Sprintf("spike1-%d", time.Now().Unix())
	apiDomain := fmt.Sprintf("api.%s.%s", appID, zone)
	emailDomain := fmt.Sprintf("%s.%s", appID, zone)

	program := buildProgram(zone, appID, apiDomain, emailDomain)

	ctx := context.Background()
	stack, err := auto.UpsertStackInlineSource(ctx, stackName, projectName, program,
		auto.EnvVars(map[string]string{
			"PULUMI_CONFIG_PASSPHRASE": passphrase,
		}),
	)
	if err != nil {
		fatal("create/select stack", err)
	}

	if *destroy {
		fmt.Println("destroying spike 1 stack...")
		if _, err := stack.Destroy(ctx, optdestroy.ProgressStreams(os.Stdout)); err != nil {
			fatal("pulumi destroy", err)
		}
		fmt.Println("destroy complete.")
		return
	}

	fmt.Printf("app id:      %s\n", appID)
	fmt.Printf("api domain:  %s\n", apiDomain)
	fmt.Printf("email domain: %s\n", emailDomain)
	fmt.Println("running pulumi up (single pass, no manual DNS step expected)...")

	res, err := stack.Up(ctx, optup.ProgressStreams(os.Stdout))
	if err != nil {
		fatal("pulumi up", err)
	}

	fmt.Println("\n--- outputs ---")
	for k, v := range res.Outputs {
		fmt.Printf("%s: %v\n", k, v.Value)
	}
	fmt.Println("\nspike 1 up complete: ACM certificate ISSUED and SES identity Verified in one pass.")
	fmt.Println("tear down with: pulumi destroy -s " + stackName + " (from spikes/launchpad-v0, or `go run . -destroy`)")
}

func buildProgram(zone, appID, apiDomain, emailDomain string) pulumi.RunFunc {
	return func(ctx *pulumi.Context) error {
		zoneRes, err := cloudflare.LookupZone(ctx, &cloudflare.LookupZoneArgs{Name: &zone})
		if err != nil {
			return fmt.Errorf("looking up cloudflare zone %q: %w", zone, err)
		}

		tags := pulumi.StringMap{
			"houston:spike":  pulumi.String(spikeTag),
			"houston:app-id": pulumi.String(appID),
		}

		cert, err := acm.NewCertificate(ctx, "api-cert", &acm.CertificateArgs{
			DomainName:       pulumi.String(apiDomain),
			ValidationMethod: pulumi.String("DNS"),
			Tags:             tags,
		})
		if err != nil {
			return fmt.Errorf("creating ACM certificate: %w", err)
		}

		identity, err := ses.NewDomainIdentity(ctx, "email-identity", &ses.DomainIdentityArgs{
			Domain: pulumi.String(emailDomain),
		})
		if err != nil {
			return fmt.Errorf("creating SES domain identity: %w", err)
		}

		validationOption := cert.DomainValidationOptions.Index(pulumi.Int(0))

		acmRecord, err := cloudflare.NewRecord(ctx, "acm-validation-record", &cloudflare.RecordArgs{
			ZoneId:  pulumi.String(zoneRes.Id),
			Name:    trimTrailingDot(validationOption.ResourceRecordName().Elem()),
			Type:    validationOption.ResourceRecordType().Elem(),
			Content: trimTrailingDot(validationOption.ResourceRecordValue().Elem()),
			Ttl:     pulumi.Int(60),
			Comment: pulumi.String(appID),
		})
		if err != nil {
			return fmt.Errorf("creating Cloudflare ACM validation record: %w", err)
		}

		sesRecord, err := cloudflare.NewRecord(ctx, "ses-verification-record", &cloudflare.RecordArgs{
			ZoneId:  pulumi.String(zoneRes.Id),
			Name:    pulumi.String(fmt.Sprintf("_amazonses.%s", emailDomain)),
			Type:    pulumi.String("TXT"),
			Content: identity.VerificationToken,
			Ttl:     pulumi.Int(60),
			Comment: pulumi.String(appID),
		})
		if err != nil {
			return fmt.Errorf("creating Cloudflare SES verification record: %w", err)
		}

		_, err = acm.NewCertificateValidation(ctx, "cert-validation", &acm.CertificateValidationArgs{
			CertificateArn: cert.Arn,
		}, pulumi.DependsOn([]pulumi.Resource{acmRecord}))
		if err != nil {
			return fmt.Errorf("waiting for ACM certificate validation: %w", err)
		}

		_, err = ses.NewDomainIdentityVerification(ctx, "email-verification", &ses.DomainIdentityVerificationArgs{
			Domain: identity.Domain,
		}, pulumi.DependsOn([]pulumi.Resource{sesRecord}))
		if err != nil {
			return fmt.Errorf("waiting for SES domain verification: %w", err)
		}

		ctx.Export("appId", pulumi.String(appID))
		ctx.Export("apiDomain", pulumi.String(apiDomain))
		ctx.Export("emailDomain", pulumi.String(emailDomain))
		ctx.Export("certArn", cert.Arn)
		ctx.Export("sesIdentityArn", identity.Arn)
		return nil
	}
}

// Cloudflare rejects a trailing dot on record name/content that ACM's FQDN outputs always carry.
func trimTrailingDot(s pulumi.StringOutput) pulumi.StringOutput {
	return s.ApplyT(func(v string) string {
		return strings.TrimSuffix(v, ".")
	}).(pulumi.StringOutput)
}

func fatal(step string, err error) {
	fmt.Fprintf(os.Stderr, "%s: %v\n", step, err)
	os.Exit(1)
}
