# Bash scripts

These Bash scripts were written using LLMs.

## extract-file-history.sh

[extract-file-history.sh](https://raw.githubusercontent.com/simonw/tools/refs/heads/main/bash/extract-file-history.sh)

Create a brand new GitHub repository and copy the history of a single file from another repository into it.

```bash
./extract-file-history.sh path/to/repo file-path-within-repo.txt path/to/new-repo [optional-new-file-name]
```

I used it to create [this file history](https://github.com/simonw/llm-prices/commits/9a64678aa4635131dbb916ec99a735ee54050db1/) from [simonw/tools](https://github.com/simonw/tools):

```bash
git clone https://github.com/simonw/tools
./extract-file-history.sh tools llm-prices.html llm-prices index.html
```

## mem.sh

[mem.sh](https://raw.githubusercontent.com/simonw/tools/refs/heads/main/bash/mem.sh)

On macOS show the memory usage of the top processes, grouped by name. E.g.

```bash
./mem.sh
```
```
   11.58 GB	  167	Visual Studio Code.app/Contents/Frameworks/Code Helper (Plugin).app/Contents/MacOS/Code Helper (Plugin)
   11.21 GB	   54	Visual Studio Code.app/Contents/Frameworks/Code Helper (Renderer).app/Contents/MacOS/Code Helper (Renderer)
    2.51 GB	   56	Visual Studio Code.app/Contents/Frameworks/Code Helper.app/Contents/MacOS/Code Helper
    2.10 GB	   12	Firefox.app/Contents/MacOS/plugin-container.app/Contents/MacOS/plugin-container
  541.83 MB	    1	Firefox.app/Contents/MacOS/firefox
  456.03 MB	    1	Visual Studio Code.app/Contents/MacOS/Electron
  ...
```
