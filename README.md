# gr-iridiumtx
gr-iridiumtx it's a project extending the functionality of gr-iridium (add link) with the functionality to encode and modulate binary streams of valid Iridium bursts on the L-band link. The main functionality is the multi_gen.py, which takes a file as a input of iridium binary streams as in the output of collected Iridium binary streams with gr-iridium and outputs a SigMF file with the modulated binary streams onto the 10 MHz spectrum. This file then can be send over to any SDR that supports this spectrum and at the center frequency of Iridium L-band link.

Thus this tool can be used to generate legitimate Iridium signals to be sent over to legitimate Iridium devices to inject messages.

## Disclaimer
Regulations for transmitting on the Iridium L-band vary by country. Use this tool responsibly ideally only inside a faraday cage. Failing to use this tool responsibly may result in criminal offense. Creators of this tool do not take responsibility for any nefarious usage of this tool.

## Installation
Installation tested on Ubuntu 22.04, Python 3.10, GNURadio 3.10.

```
sudo apt install gnuradio-dev gr-osmosdr cmake libsndfile1-dev doxygen

git clone https://github.com/n00tzer0/gr-iridiumtx
cd gr-iridiumtx
cmake -B build
cmake --build build
sudo cmake --install build
sudo ldconfig
```


## Usage
For generating SigMF files from recorded or created Iridium traffic. The recorded text output from gr-iridium can be replayed into a SigMF file. Example of the Ring alerts are presented in the sample-data directory. 

```
python3 python/iridiumtx/multi_gen.py <input text file>
```


