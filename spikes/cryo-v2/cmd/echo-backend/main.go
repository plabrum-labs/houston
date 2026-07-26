// echo-backend is a trivial TCP "app" for spike 3 (xDS propagation): it
// answers every connection with its own INSTANCE_ID so a test script can
// tell which endpoint actually served a request as Envoy's routing changes.
package main

import (
	"fmt"
	"log"
	"net"
	"os"
)

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	id := os.Getenv("INSTANCE_ID")
	if id == "" {
		id = "unknown"
	}

	l, err := net.Listen("tcp", ":"+port)
	if err != nil {
		log.Fatal(err)
	}
	log.Printf("echo-backend %s listening on :%s", id, port)

	for {
		conn, err := l.Accept()
		if err != nil {
			continue
		}
		go func(c net.Conn) {
			defer c.Close()
			fmt.Fprintf(c, "%s\n", id)
		}(conn)
	}
}
