// scheduler-harness is the spike 4 harness for docs/platforms/cryo/v2/spikes.md:
// confirms that concurrent placement triggers for the same not-yet-assigned
// app resolve to exactly one registry write, with every trigger observing
// and reusing that one assignment. Not the real Cryo scheduler — just its
// serialization claim, isolated and driven over the network from real ECS
// hardware.
package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/redis/go-redis/v9"
)

var (
	rdb     *redis.Client
	locksMu sync.Mutex
	locks   = map[string]*sync.Mutex{}
)

// computeDelay simulates real placement work (bin-packing, capacity checks)
// between reading the registry and writing to it — without it, two racing
// requests are likely to both observe "unassigned" and both compute a
// winner before either write lands, which is exactly the race this spike
// needs to be able to catch if the lock were missing or wrong.
const computeDelay = 75 * time.Millisecond

func main() {
	redisAddr := envOr("REDIS_ADDR", "127.0.0.1:6379")
	port := envOr("PORT", "9000")

	rdb = redis.NewClient(&redis.Options{Addr: redisAddr})
	defer rdb.Close()

	http.HandleFunc("/trigger", handleTrigger)
	http.HandleFunc("/reset", handleReset)

	log.Printf("scheduler-harness listening on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

type triggerResponse struct {
	App        string `json:"app"`
	Assignment string `json:"assignment"`
	Created    bool   `json:"created"`
}

func handleTrigger(w http.ResponseWriter, r *http.Request) {
	app := r.URL.Query().Get("app")
	if app == "" {
		http.Error(w, "missing app", http.StatusBadRequest)
		return
	}

	lock := lockFor(app)
	lock.Lock()
	defer lock.Unlock()

	ctx := r.Context()
	key := "spike:assignment:" + app

	existing, err := rdb.Get(ctx, key).Result()
	if err == nil {
		json.NewEncoder(w).Encode(triggerResponse{App: app, Assignment: existing, Created: false})
		return
	}
	if err != redis.Nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Not yet assigned: simulate placement computation, then commit. Every
	// call generates its own random candidate so a race would be visible as
	// different assignment values across concurrent callers, not just a
	// theoretical possibility.
	time.Sleep(computeDelay)
	candidate := "task-" + randHex(6)

	if err := rdb.Set(ctx, key, candidate, 0).Err(); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(triggerResponse{App: app, Assignment: candidate, Created: true})
}

func handleReset(w http.ResponseWriter, r *http.Request) {
	app := r.URL.Query().Get("app")
	if app == "" {
		http.Error(w, "missing app", http.StatusBadRequest)
		return
	}
	rdb.Del(r.Context(), "spike:assignment:"+app)
	w.WriteHeader(http.StatusNoContent)
}

func lockFor(app string) *sync.Mutex {
	locksMu.Lock()
	defer locksMu.Unlock()
	l, ok := locks[app]
	if !ok {
		l = &sync.Mutex{}
		locks[app] = l
	}
	return l
}

func randHex(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return hex.EncodeToString(b)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
