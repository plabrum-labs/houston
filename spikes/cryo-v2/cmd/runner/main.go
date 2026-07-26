// runner is the spike harness for spikes 1 and 2 in
// docs/platforms/cryo/v2/spikes.md: fork-to-ready latency, and nested
// cgroup v2 delegation inside one ECS task. It is not the real Cryo runner —
// just enough of its fork/isolate/proxy path to measure both claims against
// real hardware.
package main

import (
	"fmt"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"syscall"
	"time"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: runner <latency|cgroup-enforce|rss-guard>")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "latency":
		runLatency()
	case "cgroup-enforce":
		runCgroupEnforce()
	case "rss-guard":
		runRSSGuard()
	default:
		fmt.Fprintf(os.Stderr, "unknown mode %q\n", os.Args[1])
		os.Exit(1)
	}
}

// --- shared cgroup v2 helpers -----------------------------------------

// cgroupBase is the container's own cgroup root. Under Docker/ECS's default
// private cgroup namespace, /sys/fs/cgroup *is* the delegated boundary, so a
// child directory created here is the actual delegation test from spike 2.
const cgroupBase = "/sys/fs/cgroup"

func enableControllers() error {
	return os.WriteFile(filepath.Join(cgroupBase, "cgroup.subtree_control"), []byte("+memory +cpu"), 0644)
}

func createChildCgroup(name string) (string, error) {
	dir := filepath.Join(cgroupBase, name)
	if err := os.Mkdir(dir, 0755); err != nil {
		return "", err
	}
	return dir, nil
}

func setMemoryMax(dir string, bytes int64) error {
	return os.WriteFile(filepath.Join(dir, "memory.max"), []byte(strconv.FormatInt(bytes, 10)), 0644)
}

func addPid(dir string, pid int) error {
	return os.WriteFile(filepath.Join(dir, "cgroup.procs"), []byte(strconv.Itoa(pid)), 0644)
}

// --- spike 1 + spike 2 combined: cold-start latency under real isolation ---

func runLatency() {
	iterations := envInt("ITERATIONS", 50)
	backendPath := envOr("BACKEND_PATH", "/usr/local/bin/backend")
	sockDir := envOr("SOCKET_DIR", "/run/spike")
	uid := uint32(envInt("RUN_UID", 65534))
	gid := uint32(envInt("RUN_GID", 65534))

	// 0777: the backend binds this socket after dropping to a non-root uid,
	// so it needs write access to the directory the root-run runner created.
	os.MkdirAll(sockDir, 0777)
	os.Chmod(sockDir, 0777)

	delegationOK := true
	if err := enableControllers(); err != nil {
		fmt.Printf("delegation,enable_controllers,fail,%v\n", err)
		delegationOK = false
	} else {
		fmt.Println("delegation,enable_controllers,ok,")
	}

	fmt.Println("iteration,fork_to_ready_us,ready_to_firstbyte_us,fork_to_firstbyte_us,cgroup_delegation")

	for i := 0; i < iterations; i++ {
		result := runOnce(i, backendPath, sockDir, uid, gid, delegationOK)
		fmt.Println(result)
	}
}

func runOnce(i int, backendPath, sockDir string, uid, gid uint32, delegationOK bool) string {
	sockPath := filepath.Join(sockDir, fmt.Sprintf("backend-%d.sock", i))
	os.Remove(sockPath)

	r, w, err := os.Pipe()
	if err != nil {
		return fmt.Sprintf("%d,error,error,error,error: pipe: %v", i, err)
	}

	cmd := exec.Command(backendPath)
	cmd.Env = append(os.Environ(), "SOCKET_PATH="+sockPath)
	cmd.ExtraFiles = []*os.File{w}
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Credential: &syscall.Credential{Uid: uid, Gid: gid},
	}
	cmd.Stderr = os.Stderr

	tFork := time.Now()
	if err := cmd.Start(); err != nil {
		w.Close()
		r.Close()
		return fmt.Sprintf("%d,error,error,error,error: start: %v", i, err)
	}
	w.Close() // parent's copy of the write end must close or the read below blocks forever

	cgroupStatus := "skipped"
	if delegationOK {
		cgroupStatus = "ok"
		dir, err := createChildCgroup(fmt.Sprintf("spike-%d", i))
		if err != nil {
			cgroupStatus = "fail: mkdir: " + err.Error()
		} else if err := setMemoryMax(dir, 64*1024*1024); err != nil {
			cgroupStatus = "fail: memory.max: " + err.Error()
		} else if err := addPid(dir, cmd.Process.Pid); err != nil {
			cgroupStatus = "fail: cgroup.procs: " + err.Error()
		}
	}

	r.SetReadDeadline(time.Now().Add(2 * time.Second))
	buf := make([]byte, 1)
	_, readyErr := r.Read(buf)
	tReady := time.Now()
	r.Close()

	var firstByteUs int64 = -1
	if readyErr == nil {
		conn, err := net.DialTimeout("unix", sockPath, time.Second)
		if err == nil {
			conn.SetDeadline(time.Now().Add(time.Second))
			conn.Write([]byte("ping"))
			out := make([]byte, 4)
			conn.Read(out)
			firstByteUs = time.Since(tReady).Microseconds()
			conn.Close()
		}
	}

	cmd.Process.Kill()
	cmd.Wait()
	os.Remove(sockPath)
	os.Remove(filepath.Join(cgroupBase, fmt.Sprintf("spike-%d", i)))

	if readyErr != nil {
		return fmt.Sprintf("%d,timeout,-,-,%s", i, cgroupStatus)
	}
	return fmt.Sprintf("%d,%d,%d,%d,%s", i, tReady.Sub(tFork).Microseconds(), firstByteUs,
		tReady.Sub(tFork).Microseconds()+firstByteUs, cgroupStatus)
}

// --- spike 2, enforcement half: does the memory limit actually get enforced? ---

func runCgroupEnforce() {
	limitBytes := int64(envInt("LIMIT_BYTES", 8*1024*1024)) // 8MB, deliberately tight

	if err := enableControllers(); err != nil {
		fmt.Printf("enforce,enable_controllers,fail,%v\n", err)
		os.Exit(1)
	}

	dir, err := createChildCgroup("spike-enforce")
	if err != nil {
		fmt.Printf("enforce,mkdir,fail,%v\n", err)
		os.Exit(1)
	}
	defer os.Remove(dir)

	if err := setMemoryMax(dir, limitBytes); err != nil {
		fmt.Printf("enforce,memory.max,fail,%v\n", err)
		os.Exit(1)
	}

	// Rule out swap absorbing the pressure instead of the kernel killing the
	// process. Not fatal if unsupported - just another data point.
	if err := os.WriteFile(filepath.Join(dir, "memory.swap.max"), []byte("0"), 0644); err != nil {
		fmt.Printf("enforce,memory.swap.max,fail,%v\n", err)
	} else {
		fmt.Println("enforce,memory.swap.max,ok,0")
	}

	// A trivial self-exec that just grows its heap until it's killed.
	cmd := exec.Command("/proc/self/exe", "__memory_hog")
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Credential: &syscall.Credential{Uid: 65534, Gid: 65534},
	}
	if err := cmd.Start(); err != nil {
		fmt.Printf("enforce,start,fail,%v\n", err)
		os.Exit(1)
	}

	if err := addPid(dir, cmd.Process.Pid); err != nil {
		fmt.Printf("enforce,cgroup.procs,fail,%v\n", err)
		cmd.Process.Kill()
		os.Exit(1)
	}

	done := make(chan error, 1)
	go func() { done <- cmd.Wait() }()

	// Poll accounting throughout, regardless of outcome, so a "not killed"
	// result is distinguishable from "never actually tracked in the cgroup".
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()
	timeout := time.After(20 * time.Second)

	for {
		select {
		case err := <-done:
			events, _ := os.ReadFile(filepath.Join(dir, "memory.events"))
			fmt.Printf("enforce,result,killed,exit=%v events=%s\n", err, strings.TrimSpace(string(events)))
			return
		case <-timeout:
			cmd.Process.Kill()
			fmt.Println("enforce,result,fail,not killed within 20s - limit not enforced")
			os.Exit(1)
		case <-ticker.C:
			current, currErr := os.ReadFile(filepath.Join(dir, "memory.current"))
			max, maxErr := os.ReadFile(filepath.Join(dir, "memory.max"))
			events, eventsErr := os.ReadFile(filepath.Join(dir, "memory.events"))
			hogRSS := readRSS(cmd.Process.Pid)
			fmt.Printf("enforce,sample,t=%s,current=%s(err=%v),max=%s(err=%v),events=%s(err=%v),hog_rss_kb=%s\n",
				time.Now().Format(time.RFC3339Nano),
				strings.TrimSpace(string(current)), currErr,
				strings.TrimSpace(string(max)), maxErr,
				strings.ReplaceAll(strings.TrimSpace(string(events)), "\n", ";"), eventsErr,
				hogRSS)
		}
	}
}

// readRSS cross-checks the hog's actual memory growth via /proc, independent
// of whatever the cgroup memory controller reports - proves whether the
// process is genuinely allocating even if cgroup accounting looks broken.
func readRSS(pid int) string {
	data, err := os.ReadFile(fmt.Sprintf("/proc/%d/status", pid))
	if err != nil {
		return "err:" + err.Error()
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(line, "VmRSS:") {
			return strings.TrimSpace(strings.TrimPrefix(line, "VmRSS:"))
		}
	}
	return "not_found"
}

// memoryHog runs when re-exec'd with __memory_hog; it just allocates until
// the kernel stops it.
func memoryHog() {
	var chunks [][]byte
	for {
		chunks = append(chunks, make([]byte, 1024*1024))
		for _, c := range chunks {
			c[0] = 1 // touch the page so it's actually committed
		}
		time.Sleep(10 * time.Millisecond)
	}
}

// sibling runs when re-exec'd with __sibling: a well-behaved backend stand-in
// that allocates a small fixed amount once and then just idles, well under
// any reasonable budget, so spike 5 can confirm it survives its runaway
// neighbor being killed.
func sibling() {
	buf := make([]byte, 2*1024*1024)
	for i := range buf {
		buf[i] = 1
	}
	select {}
}

func init() {
	if len(os.Args) > 1 {
		switch os.Args[1] {
		case "__memory_hog":
			memoryHog()
			os.Exit(0)
		case "__sibling":
			sibling()
			os.Exit(0)
		}
	}
}

// --- spike 5: runner-managed memory enforcement via RSS polling ---

const taskCgroupRoot = "/sys/fs/cgroup"

type guardedProc struct {
	name string
	pid  int
	cmd  *exec.Cmd
}

func runRSSGuard() {
	numSiblings := envInt("NUM_SIBLINGS", 5)
	budgetBytes := int64(envInt("BUDGET_BYTES", 8*1024*1024))
	pollInterval := time.Duration(envInt("POLL_INTERVAL_MS", 250)) * time.Millisecond
	taskMemLimit := int64(envInt("TASK_MEM_LIMIT_BYTES", 512*1024*1024))
	rounds := envInt("ROUNDS", 5)
	maxWait := 30 * time.Second

	for round := 0; round < rounds; round++ {
		runRSSGuardRound(round, numSiblings, budgetBytes, pollInterval, taskMemLimit, maxWait)
	}
}

func spawnGuarded(name, reexecArg string) (*guardedProc, error) {
	cmd := exec.Command("/proc/self/exe", reexecArg)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Credential: &syscall.Credential{Uid: 65534, Gid: 65534},
	}
	if err := cmd.Start(); err != nil {
		return nil, err
	}
	return &guardedProc{name: name, pid: cmd.Process.Pid, cmd: cmd}, nil
}

func readTaskMemCurrent() (int64, error) {
	data, err := os.ReadFile(filepath.Join(taskCgroupRoot, "memory.current"))
	if err != nil {
		return 0, err
	}
	return strconv.ParseInt(strings.TrimSpace(string(data)), 10, 64)
}

func alive(pid int) bool {
	return syscall.Kill(pid, 0) == nil
}

func runRSSGuardRound(round, numSiblings int, budgetBytes int64, pollInterval time.Duration, taskMemLimit int64, maxWait time.Duration) {
	var procs []*guardedProc
	defer func() {
		for _, p := range procs {
			p.cmd.Process.Kill()
			p.cmd.Wait()
		}
	}()

	for i := 0; i < numSiblings; i++ {
		p, err := spawnGuarded(fmt.Sprintf("sibling-%d", i), "__sibling")
		if err != nil {
			fmt.Printf("guard,round=%d,spawn_sibling,fail,%v\n", round, err)
			return
		}
		procs = append(procs, p)
	}
	runaway, err := spawnGuarded("runaway", "__memory_hog")
	if err != nil {
		fmt.Printf("guard,round=%d,spawn_runaway,fail,%v\n", round, err)
		return
	}
	procs = append(procs, runaway)

	start := time.Now()
	killedRunaway := false
	var killElapsed time.Duration
	var rssAtKill, taskMemAtKill int64

	deadline := time.Now().Add(maxWait)
	for time.Now().Before(deadline) {
		time.Sleep(pollInterval)

		for _, p := range procs {
			if p.name != "runaway" {
				continue
			}
			rssKB, _ := strconv.ParseInt(strings.TrimSpace(strings.TrimSuffix(readRSS(p.pid), " kB")), 10, 64)
			rssBytes := rssKB * 1024
			if rssBytes > budgetBytes {
				taskMem, _ := readTaskMemCurrent()
				syscall.Kill(p.pid, syscall.SIGKILL)
				killedRunaway = true
				killElapsed = time.Since(start)
				rssAtKill = rssBytes
				taskMemAtKill = taskMem
			}
		}
		if killedRunaway {
			break
		}
	}

	if !killedRunaway {
		fmt.Printf("guard,round=%d,result,fail,runaway never exceeded budget or was never killed within %s\n", round, maxWait)
		return
	}

	// Give siblings a moment past the kill, then confirm they're still alive.
	time.Sleep(2 * pollInterval)
	survivors := 0
	for _, p := range procs {
		if p.name != "runaway" && alive(p.pid) {
			survivors++
		}
	}

	taskMemPct := float64(taskMemAtKill) / float64(taskMemLimit) * 100
	fmt.Printf("guard,round=%d,result,ok,kill_elapsed_ms=%d,rss_at_kill_bytes=%d,task_mem_at_kill_bytes=%d,task_mem_at_kill_pct=%.1f,siblings_survived=%d/%d\n",
		round, killElapsed.Milliseconds(), rssAtKill, taskMemAtKill, taskMemPct, survivors, numSiblings)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	v := os.Getenv(key)
	if v == "" {
		return fallback
	}
	n, err := strconv.Atoi(v)
	if err != nil {
		return fallback
	}
	return n
}
