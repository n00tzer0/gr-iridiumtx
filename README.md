# gr-iridiumtx
gr-iridiumtx it's a project extending the functionality of gr-iridium (add link) with the functionality to encode and modulate binary streams of valid Iridium bursts on the L-band link. The main functionality is the multi_gen.py, which takes a file as a input of iridium binary streams as in the output of collected Iridium binary streams with gr-iridium and outputs a SigMF file with the modulated binary streams onto the 10 MHz spectrum. This file then can be send over to any SDR that supports this spectrum and at the center frequency of Iridium L-band link.

Thus this tool can be used to generate legitimate Iridium signals to be sent over to legitimate Iridium devices to inject messages.

## Disclaimer
Regulations for transmitting on the Iridium L-band vary by country. Use this tool responsibly ideally only inside a faraday cage. Failing to use this tool responsibly may result in criminal offense. Creators of this tool do not take responsibility for any nefarious usage of this tool.

## Installation
### Requirements

```
gnuradio-dev
```


## Usage
Run multi_gen.py <input file> <>

