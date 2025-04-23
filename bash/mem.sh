#!/usr/bin/env bash
#
# mem.sh — show per‐command RSS usage, defaults to top 20 but
# pass --all to list all.

# parse flag
show_all=false
if [[ "$1" == "--all" ]]; then
  show_all=true
fi

# the core pipeline, without sorting/limiting
pipeline() {
  ps -xmo rss,comm |
    awk 'NR>1 {
      rss = $1
      $1 = ""                 # drop the rss field
      sub(/^ +/, "")          # trim leading spaces
      cmd = $0                # full command, spaces intact
      mem[cmd] += rss
      count[cmd]++
    }
    END {
      for (proc in mem) {
        display_name = proc
        if (proc ~ /^\/Applications\//)
          display_name = substr(proc, 15)

        memory_mb = mem[proc] / 1024
        if (memory_mb >= 1024) {
          memory_str = sprintf("%8.2f GB", memory_mb/1024)
        } else {
          memory_str = sprintf("%8.2f MB", memory_mb)
        }

        printf "%f\t%s\t%5d\t%s\n",
               memory_mb, memory_str, count[proc], display_name
      }
    }'
}

# run, then sort and optionally limit
if $show_all; then
  pipeline | sort -nr | cut -f2-
else
  pipeline | sort -nr | cut -f2- | head -n 20
fi

