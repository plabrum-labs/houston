// control-plane is the spike 3 harness for docs/platforms/cryo/v2/spikes.md:
// a minimal go-control-plane ADS server that watches one Redis key
// (comma-separated "host:port" endpoints) and pushes an updated Cluster +
// ClusterLoadAssignment to Envoy whenever it changes. Not the real Cryo xDS
// translator — just enough to measure registry-change-to-Envoy-reflects-it
// latency end to end.
package main

import (
	"context"
	"log"
	"net"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"

	clusterv3 "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	corev3 "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	endpointv3 "github.com/envoyproxy/go-control-plane/envoy/config/endpoint/v3"
	discoverygrpc "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v3"
	cachetypes "github.com/envoyproxy/go-control-plane/pkg/cache/types"
	cachev3 "github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	resourcev3 "github.com/envoyproxy/go-control-plane/pkg/resource/v3"
	serverv3 "github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"github.com/redis/go-redis/v9"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/durationpb"
	"google.golang.org/protobuf/types/known/wrapperspb"
)

const clusterName = "demo_cluster"

func main() {
	redisAddr := envOr("REDIS_ADDR", "127.0.0.1:6379")
	redisKey := envOr("REDIS_KEY", "spike:endpoints")
	grpcPort := envOr("GRPC_PORT", "18000")
	pollInterval := 100 * time.Millisecond

	rdb := redis.NewClient(&redis.Options{Addr: redisAddr})
	defer rdb.Close()

	snapshotCache := cachev3.NewSnapshotCache(false, cachev3.IDHash{}, nil)
	srv := serverv3.NewServer(context.Background(), snapshotCache, nil)

	grpcServer := grpc.NewServer()
	discoverygrpc.RegisterAggregatedDiscoveryServiceServer(grpcServer, srv)

	lis, err := net.Listen("tcp", ":"+grpcPort)
	if err != nil {
		log.Fatalf("listen: %v", err)
	}
	go func() {
		log.Printf("control-plane ADS listening on :%s", grpcPort)
		if err := grpcServer.Serve(lis); err != nil {
			log.Fatalf("serve: %v", err)
		}
	}()

	watchRedis(rdb, redisKey, pollInterval, snapshotCache)
}

func watchRedis(rdb *redis.Client, key string, interval time.Duration, cache cachev3.SnapshotCache) {
	ctx := context.Background()
	var lastRaw string
	version := 0

	for {
		val, err := rdb.Get(ctx, key).Result()
		if err != nil && err != redis.Nil {
			log.Printf("redis get error: %v", err)
			time.Sleep(interval)
			continue
		}

		if val != lastRaw {
			t0 := time.Now()
			version++
			endpoints := parseEndpoints(val)
			snap, err := buildSnapshot(strconv.Itoa(version), endpoints)
			if err != nil {
				log.Printf("build snapshot: %v", err)
			} else if err := cache.SetSnapshot(ctx, "spike-node", snap); err != nil {
				log.Printf("set snapshot: %v", err)
			} else {
				log.Printf("redis_change,version=%d,endpoints=%v,snapshot_pushed_us=%d",
					version, endpoints, time.Since(t0).Microseconds())
			}
			lastRaw = val
		}

		time.Sleep(interval)
	}
}

func parseEndpoints(raw string) []string {
	if raw == "" {
		return nil
	}
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p != "" {
			out = append(out, p)
		}
	}
	sort.Strings(out)
	return out
}

func buildSnapshot(version string, endpoints []string) (*cachev3.Snapshot, error) {
	var lbEndpoints []*endpointv3.LbEndpoint
	for _, ep := range endpoints {
		host, portStr, err := net.SplitHostPort(ep)
		if err != nil {
			continue
		}
		port, err := strconv.Atoi(portStr)
		if err != nil {
			continue
		}
		lbEndpoints = append(lbEndpoints, &endpointv3.LbEndpoint{
			HostIdentifier: &endpointv3.LbEndpoint_Endpoint{
				Endpoint: &endpointv3.Endpoint{
					Address: &corev3.Address{
						Address: &corev3.Address_SocketAddress{
							SocketAddress: &corev3.SocketAddress{
								Address: host,
								PortSpecifier: &corev3.SocketAddress_PortValue{
									PortValue: uint32(port),
								},
							},
						},
					},
				},
			},
		})
	}

	cla := &endpointv3.ClusterLoadAssignment{
		ClusterName: clusterName,
		Endpoints: []*endpointv3.LocalityLbEndpoints{
			{LbEndpoints: lbEndpoints},
		},
	}

	cluster := &clusterv3.Cluster{
		Name:                 clusterName,
		ConnectTimeout:       durationpb.New(1 * time.Second),
		ClusterDiscoveryType: &clusterv3.Cluster_Type{Type: clusterv3.Cluster_STATIC},
		LbPolicy:             clusterv3.Cluster_ROUND_ROBIN,
		LoadAssignment:       cla,
		HealthChecks: []*corev3.HealthCheck{
			{
				Timeout:            durationpb.New(2 * time.Second),
				Interval:           durationpb.New(1 * time.Second),
				UnhealthyThreshold: wrapperspb.UInt32(2),
				HealthyThreshold:   wrapperspb.UInt32(1),
				HealthChecker: &corev3.HealthCheck_TcpHealthCheck_{
					TcpHealthCheck: &corev3.HealthCheck_TcpHealthCheck{},
				},
			},
		},
	}

	resources := map[resourcev3.Type][]cachetypes.Resource{
		resourcev3.ClusterType: {cluster},
	}

	return cachev3.NewSnapshot(version, resources)
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}
