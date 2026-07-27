// Entry point for the Launchpad v0 spikes (docs/platforms/launchpad/v0/spikes.md).
// Each spike is a self-contained Go Automation API program against real AWS
// and/or Cloudflare infrastructure. Select one with -spike; -destroy tears
// down that spike's stack (and any throwaway infra it started) instead of
// standing it up.
package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	spike := flag.Int("spike", 1, "which spike to run: 1 (cross-provider reconciliation), 2 (protected resource), 3 (credential scoping)")
	destroy := flag.Bool("destroy", false, "tear down the spike's stack instead of running it")
	flag.Parse()

	switch *spike {
	case 1:
		runSpike1(*destroy)
	case 2:
		runSpike2(*destroy)
	case 3:
		runSpike3(*destroy)
	default:
		fmt.Fprintf(os.Stderr, "unknown -spike=%d (want 1, 2, or 3)\n", *spike)
		os.Exit(1)
	}
}
