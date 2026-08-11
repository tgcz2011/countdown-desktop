package version

// Version is injected at build time via -ldflags.
// Format: a.b.c.d
// - a: major (breaking/significant new architecture)
// - b: minor (significant feature additions)
// - c: patch (small feature additions)
// - d: build (bug fixes, tweaks)
var Version = "1.0.0.2"

// BuildTime is injected at build time.
var BuildTime = "unknown"

// GitCommit is injected at build time.
var GitCommit = "unknown"
