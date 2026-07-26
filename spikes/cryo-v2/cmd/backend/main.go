// backend is the trivial static binary the runner forks. It listens on a
// unix socket, signals readiness once by writing a byte to its inherited
// fd 3, then echoes whatever it receives back to the caller — just enough
// to let the runner measure fork-to-first-byte latency.
package main

import (
	"net"
	"os"
)

func main() {
	socketPath := os.Getenv("SOCKET_PATH")
	if socketPath == "" {
		os.Exit(1)
	}

	os.Remove(socketPath)
	l, err := net.Listen("unix", socketPath)
	if err != nil {
		os.Exit(1)
	}
	defer l.Close()

	// fd 3 is the write end of a pipe the runner passed via ExtraFiles.
	readiness := os.NewFile(3, "readiness")
	if readiness != nil {
		readiness.Write([]byte{1})
		readiness.Close()
	}

	for {
		conn, err := l.Accept()
		if err != nil {
			return
		}
		go handle(conn)
	}
}

func handle(conn net.Conn) {
	defer conn.Close()
	buf := make([]byte, 4096)
	for {
		n, err := conn.Read(buf)
		if n > 0 {
			conn.Write(buf[:n])
		}
		if err != nil {
			return
		}
	}
}
