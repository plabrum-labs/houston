// Spike: protected resource under a bad reconciliation.
//
// Tests the Launchpad v0 design's claim that a stateful resource — an app's
// database schema and role — cannot be destroyed or replaced as a side
// effect of reconciling a declared configuration. The program provisions a
// postgresql.Schema and postgresql.Role keyed by an immutable app ID, both
// protected, then reconciles a "bad" program that simulates a real class of
// bug: a refactor that accidentally derives both the resources' Pulumi
// logical identity and their underlying database object names from the
// app's mutable display name instead of its immutable ID. That orphans the
// old, correctly-named objects — Pulumi should refuse to delete the
// protected originals rather than dropping them once nothing references
// them anymore.
//
// Runs against a throwaway local Postgres in Docker — the design's claim
// under test is about Pulumi's protect mechanism, not about real RDS, so a
// disposable local instance is a faithful and much cheaper stand-in.
package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/pulumi/pulumi-postgresql/sdk/v3/go/postgresql"
	"github.com/pulumi/pulumi/sdk/v3/go/auto"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optremove"
	"github.com/pulumi/pulumi/sdk/v3/go/auto/optup"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

const (
	spike2ProjectName = "launchpad-v0-spike2"
	spike2StackName   = "spike2-protected-resource"
	pgContainerName   = "houston-spike2-pg"
	pgPort            = "55432"
	pgSuperPassword   = "spikepg"
)

func runSpike2(destroy bool) {
	ctx := context.Background()

	if destroy {
		removeSpike2Stack(ctx)
		stopPostgres()
		fmt.Println("destroy complete.")
		return
	}

	startPostgres()
	defer stopPostgres()

	appID := fmt.Sprintf("app%d", time.Now().Unix())
	goodDisplayName := "Initial App"
	badDisplayName := "Renamed App"

	stack, err := auto.UpsertStackInlineSource(ctx, spike2StackName, spike2ProjectName,
		buildSpike2Program(appID, goodDisplayName, false),
		auto.EnvVars(map[string]string{
			"PULUMI_CONFIG_PASSPHRASE": passphrase,
		}),
	)
	if err != nil {
		fatal("create/select stack", err)
	}

	fmt.Printf("app id: %s\n", appID)
	fmt.Println("\n--- pass 1: good reconciliation (creates protected schema + role) ---")
	if _, err := stack.Up(ctx, optup.ProgressStreams(os.Stdout)); err != nil {
		fatal("pulumi up (good reconciliation)", err)
	}

	fmt.Println("\n--- pass 2: bad reconciliation (display name change forces resource identity to shift) ---")
	stack.Workspace().SetProgram(buildSpike2Program(appID, badDisplayName, true))
	_, badErr := stack.Up(ctx, optup.ProgressStreams(os.Stdout))

	fmt.Println("\n--- verifying protected objects still exist in postgres ---")
	roleName := "app_role_" + appID
	schemaName := "app_" + appID
	roleIntact := pgObjectExists("SELECT 1 FROM pg_roles WHERE rolname = '" + roleName + "'")
	schemaIntact := pgObjectExists("SELECT 1 FROM pg_namespace WHERE nspname = '" + schemaName + "'")
	fmt.Printf("role %q intact: %v\n", roleName, roleIntact)
	fmt.Printf("schema %q intact: %v\n", schemaName, schemaIntact)

	pass := badErr != nil && strings.Contains(strings.ToLower(badErr.Error()), "protect") && roleIntact && schemaIntact
	fmt.Println()
	if pass {
		fmt.Println("RESULT: PASS — Pulumi refused the bad reconciliation and the protected schema/role were untouched.")
	} else {
		fmt.Println("RESULT: FAIL — the bad reconciliation did not error on protection, or the protected objects were changed.")
		if badErr == nil {
			fmt.Println("  (pulumi up for the bad reconciliation succeeded, which should not have happened)")
		} else {
			fmt.Printf("  bad reconciliation error: %v\n", badErr)
		}
	}

	fmt.Println("\ntearing down...")
	// The bad pass, if it got far enough to hit protection, leaves the stack
	// holding both the original protected objects (undeleted, by design) and
	// a second set it managed to create before the delete it wanted was
	// refused. Reconciling that mixed state back to clean via `pulumi
	// destroy` would mean unprotecting four resources first. Since this is a
	// throwaway local Postgres container that's about to be removed
	// entirely (taking every object with it), it's simpler and just as
	// clean to drop the container and then force-remove the stack's
	// bookkeeping outright rather than reconcile through it.
	removeSpike2Stack(ctx)
}

func removeSpike2Stack(ctx context.Context) {
	stack, err := auto.SelectStackInlineSource(ctx, spike2StackName, spike2ProjectName, noopProgram)
	if err != nil {
		return
	}
	fmt.Println("removing spike 2 stack...")
	if err := stack.Workspace().RemoveStack(ctx, spike2StackName, optremove.Force()); err != nil {
		fmt.Fprintf(os.Stderr, "removing stack: %v\n", err)
	}
}

// buildSpike2Program returns the reconciliation program for one app. When
// bug is true, it simulates the class of bug the spike targets: both the
// Pulumi logical resource names (which determine resource identity/URN) and
// the underlying database object names are built from the app's mutable
// display name instead of its immutable ID. A correct program keys both by
// appID always; the spike exists to confirm protect{} catches this bug
// rather than silently orphaning and dropping the original objects.
func buildSpike2Program(appID, displayName string, bug bool) pulumi.RunFunc {
	return func(ctx *pulumi.Context) error {
		provider, err := postgresql.NewProvider(ctx, "local-pg", &postgresql.ProviderArgs{
			Host:      pulumi.String("localhost"),
			Port:      pulumi.Int(mustAtoi(pgPort)),
			Username:  pulumi.String("postgres"),
			Password:  pulumi.String(pgSuperPassword),
			Sslmode:   pulumi.String("disable"),
			Superuser: pulumi.Bool(true),
		})
		if err != nil {
			return fmt.Errorf("configuring postgres provider: %w", err)
		}
		opts := []pulumi.ResourceOption{pulumi.Provider(provider), pulumi.Protect(true)}

		key := appID
		if bug {
			key = slugify(displayName)
		}

		role, err := postgresql.NewRole(ctx, "role-"+key, &postgresql.RoleArgs{
			Name:  pulumi.String("app_role_" + key),
			Login: pulumi.Bool(true),
		}, opts...)
		if err != nil {
			return fmt.Errorf("creating role: %w", err)
		}

		schema, err := postgresql.NewSchema(ctx, "schema-"+key, &postgresql.SchemaArgs{
			Name:  pulumi.String("app_" + key),
			Owner: role.Name,
		}, opts...)
		if err != nil {
			return fmt.Errorf("creating schema: %w", err)
		}

		ctx.Export("appId", pulumi.String(appID))
		ctx.Export("displayName", pulumi.String(displayName))
		ctx.Export("roleName", role.Name)
		ctx.Export("schemaName", schema.Name)
		return nil
	}
}

func noopProgram(ctx *pulumi.Context) error { return nil }

func mustAtoi(s string) int {
	n, err := strconv.Atoi(s)
	if err != nil {
		fatal("parsing port", err)
	}
	return n
}

var nonAlnum = regexp.MustCompile(`[^a-z0-9]+`)

func slugify(s string) string {
	return strings.Trim(nonAlnum.ReplaceAllString(strings.ToLower(s), "_"), "_")
}

func startPostgres() {
	fmt.Println("starting throwaway postgres in docker...")
	exec.Command("docker", "rm", "-f", pgContainerName).Run() //nolint:errcheck // best-effort cleanup of a stale container
	run := exec.Command("docker", "run", "-d", "--rm",
		"--name", pgContainerName,
		"-e", "POSTGRES_PASSWORD="+pgSuperPassword,
		"-p", pgPort+":5432",
		"postgres:16-alpine",
	)
	run.Stdout = os.Stdout
	run.Stderr = os.Stderr
	if err := run.Run(); err != nil {
		fatal("docker run postgres", err)
	}

	deadline := time.Now().Add(30 * time.Second)
	for time.Now().Before(deadline) {
		if exec.Command("docker", "exec", pgContainerName, "pg_isready", "-U", "postgres").Run() == nil {
			fmt.Println("postgres is ready.")
			return
		}
		time.Sleep(time.Second)
	}
	fatal("waiting for postgres to become ready", fmt.Errorf("timed out after 30s"))
}

func stopPostgres() {
	fmt.Println("stopping throwaway postgres...")
	if err := exec.Command("docker", "rm", "-f", pgContainerName).Run(); err != nil {
		fmt.Fprintf(os.Stderr, "docker rm %s: %v\n", pgContainerName, err)
	}
}

func pgObjectExists(query string) bool {
	out, err := exec.Command("docker", "exec", pgContainerName, "psql", "-U", "postgres", "-tAc", query).Output()
	if err != nil {
		fmt.Fprintf(os.Stderr, "verifying postgres state: %v\n", err)
		return false
	}
	return strings.TrimSpace(string(out)) == "1"
}
