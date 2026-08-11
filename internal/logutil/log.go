package logutil

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

var (
	mu   sync.Mutex
	file *os.File
)

// Init opens the log file next to the executable.
func Init() error {
	mu.Lock()
	defer mu.Unlock()
	exe, err := os.Executable()
	if err != nil {
		return err
	}
	path := filepath.Join(filepath.Dir(exe), "log.txt")
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	if err != nil {
		return err
	}
	file = f
	return nil
}

// Log writes a timestamped line to log.txt and stdout.
func Log(format string, args ...interface{}) {
	line := fmt.Sprintf("[%s] %s", time.Now().Format("2006-01-02 15:04:05"), fmt.Sprintf(format, args...))
	fmt.Println(line)
	mu.Lock()
	defer mu.Unlock()
	if file != nil {
		fmt.Fprintln(file, line)
	}
}

// Close closes the log file.
func Close() {
	mu.Lock()
	defer mu.Unlock()
	if file != nil {
		file.Close()
		file = nil
	}
}
