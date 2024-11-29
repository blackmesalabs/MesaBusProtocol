# MesaBusProtocol
Flexible Byte transport protocol for bus bridging CPUs to FPGAs over UART,SPI,SERDES physical interfaces

Mesa Bus Protocol is intended to transfer data between 50 Kbps up to 10 Gbps over UART to SERDES links with just a few wires and very little hardware overhead. It is a very small gate foot print byte transport protocol for encapsulating and transferring payloads of higher protocols (0-255 bytes per payload). Think of it like a cross between Ethernet and USB 3.1. The advantages Mesa Bus Protocol has over USB, Ethernet and PCI is that it fits easily within a $3 FPGA and may be bus mastered either by a PC with a FTDI cable or any old ARM/AVR Arduino CPU (or RPi) with just two standard UART serial port pins. As it is ASCII based, Mesa Bus Protocol is also very portable to wireless devices such as Bluetooth SPP and the RockBLOCK satellite modem for the Iridium network . MBP supports daisy chaining of up to 250 devices, allowing a single CPU bus master to communicate ( with latency ) to multiple FPGAs using a single serial interface.

This Repo is a misc collection of Python and Verilog examples for using Mesa Bus Protocol. 

For complete actual designs, see the TARball of these projects ( reside on my public Dropbox )

FTDI UART Example : https://blackmesalabs.wordpress.com/2016/10/24/sump2-96-msps-logic-analyzer-for-22/

SPI Example : https://blackmesalabs.wordpress.com/2016/12/22/sump2-100-msps-32bit-logic-analyzer-for-icoboardraspberrypi/


[ Files ]

mesa_bus3.txt : Detailed description of the protocol and how used.
  
bd_server.py : Python Example of FTDI UART for Mesa Bus access.

bd_server.ini : Example config file for bd_server.py.

ico_gpio.py : Python example of Pi SPI for Mesa Bus access.

hlist.txt : ChipVault hierarchy file for Verilog files.

top.v  : Top level FPGA for MesaBus on Digilent BASYS3 Artix7 board. 

mesa2ctrl.v : Decodes the 0xF subslot controls.

mesa2lb.v : Decodes subslot-0 bus cycles to 32bit Local Bus ( virtual PCI ).

mesa_ascii2nibble.v : Used by UART designs, converts ASCII hex to binary nibbles.

mesa_byte2ascii.v : Used by UART designs, converts binary bytes to ASCII nibble pairs.

mesa_core.v : Wrapper around a bunch of Mesa Bus verilog files for SPI.

mesa_decode.v : Main serial bus decoder. Also does daisy chain enumeration.

mesa_id.v : Reports things like Manufacture ID, Device ID, Build Timestamp.

mesa_phy.v : Wrapper around the UART blocks.

mesa_pi_spi.v : SPI interface for RaspPi.

mesa_tx_uart.v : UART TX only.

mesa_uart.v : UART RX and TX.

spi_byte2bit.v : Generic SPI serializer.

spi_prom.v : SPI interface to FPGA PROMs ( Micron ).

