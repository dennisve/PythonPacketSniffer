#!/usr/bin/python
#THIS CODE CAPTURES NETWORK PACKETS
#Only works for LINUX systems

#Socket library - neccessary to set up and extract data from sockets
import socket

#Struct library - neccessary to unpack hex structs
import struct

#Sys library - neccessary for exit() and other sys functions
import sys

#csv library - neccessary to read the protocol files (convert protocol number to text)
import csv

#Date library - needed for the errorlog
from datetime import datetime

#Creating a socket to capture all packets
def create_socket():
	#errorhandling
	try:
		#AF_PACKET 
		#SOCK_RAW receives both UDP AND TCP traffic
		#ntohs(0x0003) = ETH_P_ALL
		#network byte order to host byte order
		sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(0x0003))
		return sock

	except socket.error, errormsg:
		#writing error message to log file
		errorlog = open('errorlog.txt', 'a')
		errorlog.write(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' Socket creation failed. Code: ' + str(errormsg[0]) + 'Message ' + errormsg[1] + '\n')
		errorlog.close
		sys.exit()

#Extracting packet from socket
def extract_packet(sock):
	#packetlog = open('packetlog.txt', 'a')

	#returns packet in hex from socket with bufsize 65565
	#returns packet as string
	packet = sock.recvfrom(65565)

	#debug
	#print packet

	#create Packet object
	PacketClass = _Packet(packet[0])

	return PacketClass
                
#MAC address structure
#% indicates we want to format everything between parentheses
#.2 indicates that we always want a minimum of 2 hex numbers before each colon
#x indicates the Signed hexadecimal (lowercase) format
#ord() returns an integer representing the unicode point of the string character
def MAC_address(packet):
	MAC = "%2.2x:%2.2x:%2.2x:%2.2x:%2.2x:%2.2x" % (ord(packet[0]), ord(packet[1]), ord(packet[2]), ord(packet[3]), ord(packet[4]), ord(packet[5]))
	return MAC

def IPv6_address(packet):
	IPv6 = "%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:%2.2x%2.2x:" % (ord(packet[0]), ord(packet[1]), ord(packet[2]), ord(packet[3]), ord(packet[4]), ord(packet[5]), ord(packet[6]), ord(packet[7]), ord(packet[8]), ord(packet[9]), ord(packet[10]), ord(packet[11]), ord(packet[12]), ord(packet[13]), ord(packet[14]), ord(packet[15]))
	return IPv6

class _Packet:
	def __init__(self, packet):
		#packet length in bytes
		self.Length = len(packet)

		#we only need the unfiltered binary data
		self.Content = packet

		#extract header from Data Link Layer (OSI)
		self.DataLinkHeader = extract_ethernetheader(self.Content)
		
		if self.DataLinkHeader != None:
			#Network layer Protocol in hex (int)
			self.HexNetworkProtocol = self.DataLinkHeader.Protocol

			if self.DataLinkHeader.Protocol != None:
				#Network layer Protocol in readable text
				self.NetworkProtocol = convert_networkprotocol(self.HexNetworkProtocol)

				#extract network layer header based on DataLink protocol
				self.NetworkHeader = extract_networkheader(self.Content, self.DataLinkHeader.Protocol, self.DataLinkHeader.Length)

				if self.NetworkHeader != None:
					#Transport layer protocol in hex (int)
					self.HexTransportProtocol = self.NetworkHeader.Protocol

					if self.NetworkHeader.Protocol != None:				
						#convert transport layer protocol to readable text
						self.TransportProtocol = convert_transportprotocol(self.HexTransportProtocol)
						
						#extract transport layer header
						self.TransportHeader = extract_transportheader(self.Content, self.NetworkHeader.Protocol, self.DataLinkHeader.Length, self.NetworkHeader.Length)
		
class _EthernetHeader: 
	def __init__(self):
		#standard Ethernet header length
		self.Length = 14
		self.SourceMAC = None
		self.DestinationMAC = None
		self.Protocol = None
		self.Payload = None
		
		#default no VLAN present
		self.VLANCount = 0
		self.VLAN = []
                
	def add_VLAN(self, VLAN):
		#add VLAN information on correct position
		self.VLAN.append(VLAN)

class _VLANTag:
	def __init__(self):
		self.TPID = None
		self.PCP = None
		self.DEI = None

class _IPv4Header:
	def __init__(self):
		#standard IPv4 header length
		self.Length = 20
		self.Protocol = None
		self.Version = 4
		self.IHL = None
		self.TTL = None
		self.SourceAddress = None
		self.DestinationAddress = None

class _ARPHeader:
	def __init__(self):
		self.Length = 8
		self.Protocol = None
		self.DataLinkProtocol = None
		self.NetworkProtocol = None
		self.HardwareAddressLength = None
		self.ProtocolAddressLength = None
		self.Operation = None
		self.HardwareAddressSender = None
		self.ProtocolAddressSender = None
		self.HardwareAddressTarget = None
		self.ProtocolAddressTarget = None

class _IPv6Header:
	def __init__(self):
		self.Length = 40
		self.Protocol = None
		self.Version = None
		self.TrafficClass = None
		self.FlowLabel = None
		self.PayloadLength = None
		self.NextHeader = None
		self.HopLimit = None
		self.SourceAddress = None
		self.DestinationAddress = None

class _IPv6Address:
	def __init__(self):
		self.Address = None
		self.Type = None
		self.TypeNumber = None
		self.GlobalRoutingPrefix = None
		self.SubnetID = None
		self.InterfaceID = None
		self.LocalBit = None
		self.GlobalID = None
		self.Flags = None
		self.Scope = None
		self.GroupID = None
		

class _TCPHeader:
	def __init__(self):
		self.Length = 20
		self.SourcePort = None
		self.DestinationPort = None
		self.Sequence = None
		self.Acknowledgement = None
		self.DataOffsetReserved = None
		self.Data = None

class _UDPHeader:
	def __init__(self):
		self.Length = 8
		self.SourcePort = None
		self.DestinationPort = None
		self.Checksum = None
		self.Data = None

class _ICMPHeader:
	def __init__(self):
		self.Length = 4
		self.Type = None
		self.Code = None
		self.Checksum = None
		self.Data = None

def extract_ethernetheader(packet):
	#create _EthernetHeader object
	EthClass = _EthernetHeader()

	#First 14 bytes are ethernet header     
	eth_header = packet[0:EthClass.Length]

	#                                                       ETHERNET HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                               Ethernet dest (last 32 bits)                        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#| Ethernet dest (last 16 bits)  |Ethernet source (first 16 bits)|
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                               Ethernet source (last 32 bits)                              |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|       VLAN (optional-32bits)          |               EtherType               |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
			
	#Unpack eth_header string according to the given format !6s6sH
	#!indicates we don't know if the data is big or little endian
	#s indicates a string of characters (6xchar 6xchar)
	#H indicates an unsigned short int (1xunsigned short int)
	#Char is 1 byte, short int is 2 bytes
	#MAC address format is 6 groups of 2 hexadecimal digits
	eth = struct.unpack('!6s6sH', eth_header)

	#protocol used is short int from eth_header
	#NOTE: Some systems use little endian order (like intel)
	#we need to swap the bytes on those systems to get a uniform result
	#ntohs switches network byte order to host byte order
	#should any byte order problems occur, try implementing the ntohs function
	#eth_protocol 1500 or less? The number is the size of ethernet frame payload
	#above 1500 indicates ethernet II frame
	if eth[2]>1500:
			EthClass.Protocol = eth[2]
	else:
			EthClass.Payload = eth[2]

	#extract all VLANs if present
	EthClass = extract_VLAN(EthClass, packet)

	#add source and destination MAC
	EthClass.DestinationMAC = MAC_address(packet[0:6])
	EthClass.SourceMAC = MAC_address(packet[6:12])

	return EthClass

def extract_VLAN(EthClass, packet):
	while EthClass.Protocol == 33024:       
		#create _VLANTag object
		VLANClass = _VLANTag()
		
		#VLAN tag structure:
		#16 bits Tag Protocol Identifier (TPID) = 0x8100 or 33024
		#3 bits Priority Code Point (PCP)  --> priority of package
		#1 bit Drop Eligible Indicator (DEI) --> indicates if frame can be dropped in case of congestion
		#12 bit VLAN Identifier (VID)
		#Ethernet header grows bigger by 32 bits
		#parse VLAN tag (4bytes, eth_protocol included in the last 2 bytes)
		VLAN_tag_data = packet[EthClass.Length:EthClass.Length+4]
		
		#unpack VLAN tag
		VLANt = struct.unpack('!HH', VLAN_tag_data)
		
		#bitmask 0000 0000 0000 0111
		VLANClass.PCP = (VLANt[0] >> 13) & 0x7
		
		#bitmask 0000 0000 0000 0001
		VLANClass.DEI = (VLANt[0] >> 12) & 0x1
		
		#bitmask 0000 1111 1111 1111
		VLANClass.VID = VLANt[0] & 0xFFF
		
		#add the VLAN to the object
		EthClass.add_VLAN(VLANClass)
		
		#VLAN tag adds 4 bytes
		EthClass.Length += 4
		
		#EtherType is in the last 2 bytes
		EthClass.Protocol = VLANt[1]
		
		#number of VLAN tags depends on the number of VLAN frames
		EthClass.VLANCount += 1

	return EthClass

def convert_networkprotocol(network_protocol):
	#open the csv file with Datalink_protocols
	with open('Network_protocols.csv') as csvfile:
		
		#read fine in dictionary
		reader = csv.DictReader(csvfile)
		
		#check compare network_protocol code to codes from file
		for row in reader:
		
			#return protocol in text
			if int(row['hexcode'], 16) == network_protocol:
					return row['protocolname']

def extract_networkheader(packet, datalink_protocol, datalink_length):
	#ethertypes:
	#hex            name            decimal
	#0800           IPv4            2048
	#0806           ARP             2054
	#86DD           IPv6            34525
	#append list to listen in on other protocols
	if datalink_protocol == 2048:
		NetwClass = extract_IPv4header(packet, datalink_length)
		return NetwClass
	elif datalink_protocol == 2054:
		NetwClass = extract_ARPheader(packet, datalink_length)
		return NetwClass
	elif datalink_protocol == 34525:
		NetwClass = extract_IPv6header(packet, datalink_length)
		return NetwClass
	else:
		print 'Network protocol ' + str(datalink_protocol) + ' not supported.'
		return

#Network Layer Protocols
def extract_IPv4header(packet, datalink_length):
	#create _IPv4Header object
	IPv4Class = _IPv4Header()

	#parse the IPv4 header (first 20 characters after ethernet header)
	IPv4_header = packet[datalink_length:datalink_length+IPv4Class.Length]

	#                                                       IPv4 HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|Version|  IHL  |Type of Service|          Total Length         |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|         Identification        |Flags|      Fragment Offset    |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|  Time to Live |    Protocol   |         Header Checksum       |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                       Source Address                          |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                    Destination Address                        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+      

	#unpacking the IPv4 header
	#B unpacking to unsigned char
	#H unpacking to unsigned short int
	#s unpacking to string of 4 chars
	IPv4h = struct.unpack('!BBHHHBBH4s4s', IPv4_header)

	#version and internet header length (ihl) are in the first unsigned char
	IPv4h_version_ihl = IPv4h[0]

	#to get IPv4 version, shift 4 MSB 4 positions right
	IPv4Class.Version = (IPv4h_version_ihl >> 4) & 0xF

	#to get IPv4 internet header length, we need the 4 LSB
	#ihl & 00001111
	IPv4Class.IHL = IPv4h_version_ihl & 0xF

	#ihl is the number if 32bit words in the header
	#IPv4h_length is in bytes (*4)
	IPv4Class.Length = IPv4Class.IHL * 4

	#IPv4_ttl is unpacked on 6th position
	#B(1byte) B(1byte) H(2bytes) H(2bytes) H(2bytes) B(1byte)
	#TTL = last B
	IPv4Class.TTL = IPv4h[5]

	#IPv4 protocols:
	#hex            name            decimal
	#0006           TCP             6
	#0011           UDP             17
	#0001           ICMP            1
	#append list to listen in on other protocols
	#IPv4 protocol number is an unsigned char
	IPv4Class.Protocol = IPv4h[6]

	#convert packed source and destination IPv4 address to correct format
	#4s 4s was used to unpack
	IPv4Class.SourceAddress = socket.inet_ntoa(IPv4h[8])
	IPv4Class.DestinationAddress = socket.inet_ntoa(IPv4h[9])

	return IPv4Class
        
def extract_ARPheader(packet, datalink_length):
	#create _ARPHeader object
	ARPClass = _ARPHeader()

	#parse the ARP header 
	ARP_header = packet[datalink_length:datalink_length+ARPClass.Length]

	#                                                       ARP HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#                       Hardware type            |                Protocol type                  |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|MAC address len|Proto address l|            Operation          |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                                Sender hardware address                                |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|            ...                |   Sender protocol address     |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|            ...                |   Target hardware address     |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
	#|                              ...                              |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 
	#|                                 Target protocol address                   |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+ 

	#unpack ARP header
	#H for hardware type (2bytes)
	#H for protocol type (2bytes)
	#H for Mac address length and protocol address length (2bytes)
	#2s for operation (2bytes)

	ARPh = struct.unpack('!HHHH', ARP_header)

	#extract info
	#network protocol/hardware type (ex. ethernet = 1)
	ARPClass.DataLinkProtocol = ARPh[0]
	ARPClass.NetworkProtocol = ARPh[1]
	ARPClass.HardwareAddressLength = (ARPh[2] >> 8) & 0xF
	ARPClass.ProtocolAddressLength = ARPh[2] & 0xF
	ARPClass.Operation = ARPh[3]

	#temporary length var to avoid long sums
	ARPClass.Length += datalink_length

	#unpack hardware address sender
	#we need the length to unpack (ex MAC address is 6s)
	ARP_hardware_address_sender = packet[ARPClass.Length:ARPClass.Length+ARPClass.HardwareAddressLength]
	unpack_format_hardware = '!' + str(ARPClass.HardwareAddressLength) + 's'
	ARPClass.HardwareAddressSender = struct.unpack(unpack_format_hardware, ARP_hardware_address_sender)

	#temporary length var to avoid long sums
	ARPClass.Length += ARPClass.HardwareAddressLength

	#unpack protocol address sender
	ARP_protocol_address_sender = packet[ARPClass.Length:ARPClass.Length+ARPClass.ProtocolAddressLength]
	unpack_format_protocol = '!' + str(ARPClass.ProtocolAddressLength) + 's'
	ARPClass.ProtocolAddressSender = struct.unpack(unpack_format_protocol, ARP_protocol_address_sender)

	#temporary length var to avoid long sums
	ARPClass.Length += ARPClass.ProtocolAddressLength

	#unpack hardware address target
	ARP_hardware_address_target = packet[ARPClass.Length:ARPClass.Length+ARPClass.HardwareAddressLength]
	ARPClass.HardwareAddressTarget = struct.unpack(unpack_format_hardware, ARP_hardware_address_target)

	#temporary length var to avoid long sums
	ARPClass.Length += ARPClass.HardwareAddressLength

	#unpack protocol address target
	ARP_protocol_address_target = packet[ARPClass.Length:ARPClass.Length+ARPClass.ProtocolAddressLength]
	ARPClass.ProtocolAddressTarget = struct.unpack(unpack_format_protocol, ARP_protocol_address_target)

	#temporary length var to avoid long sums
	ARPClass.Length += ARPClass.ProtocolAddressLength

	#final length of the ARP header
	ARPClass.Length -= datalink_length

	#Hardware address to correct format
	#if we use ethernet address (MAC), we don't need the unpacked address
	#MAC_address() function will do the conversion for us
	if ARPClass.DataLinkProtocol == 1:
		ARPClass.HardwareAddressSender = MAC_address(ARP_hardware_address_sender)
		ARPClass.HardwareAddressTarget = MAC_address(ARP_hardware_address_target)
	else:
		print 'ARP hardware protocol type not supported'

	#Protocol address to correct format
	#if we use IP address (IPv4), we don't need the unpacked address
	#socket.inet_ntoa() function will do the conversion for us
	if ARPClass.NetworkProtocol == 2048:
		ARPClass.ProtocolAddressSender = socket.inet_ntoa(ARP_protocol_address_sender)
		ARPClass.ProtocolAddressTarget = socket.inet_ntoa(ARP_protocol_address_target)
	else:
		print 'ARP network protocol type not supported'

	return ARPClass

def extract_IPv6header(packet, datalink_length):
#            _____________________________________________________________________________________
#OCTET BIT  |0_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_22_23_24_25_26_27_28_29_30_31|
#  0    0   |version|  Traffic Class  |                   FLOW LABEL                              |
#OCTET BIT  |0_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_22_23_24_25_26_27_28_29_30_31|
#  4    32  |____________Payload_Lenght___________|______NEXT__HEADER_____|_______HOP__LIMIT______|
#OCTET BIT  |0_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_22_23_24_25_26_27_28_29_30_31|
#  8    64  |                                                                                     |
# 12    96  |                                    SOURCE ADDRESS                                   |
# 16    128 |                                                                                     |
# 20    160 |_____________________________________________________________________________________|
#OCTET BIT  |0_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_22_23_24_25_26_27_28_29_30_31|
# 24    192 |                                                                                     |
# 28    224 |                                  DESTINATION ADDRESS                                |
# 32    256 |                                                                                     |
# 36    288 |_____________________________________________________________________________________|
#                        _____
#                       |IPV_6|
#       VERSION                 4bits
#       Traffic Class           8bits
#       Flow Label             20bits
#       Payload lenght         16bits
#       Next header             8bits
#       Hop limit               8bits
#       SOURCE Address        128bits
#       DESTINATION address   128bits
#Pv6 addresses are represented as eight groups of four hexadecimal digits with the groups being separated by colons
	#create _IPv6Header object
	IPv6Class = _IPv6Header()

	#parse the IPv6 header (first 40 characters after ethernet header)
	IPv6_header = packet[datalink_length:datalink_length+IPv6Class.Length]

	#unpacking the IPv6 header
	#H unpacking to unsigned short int
	#I unpacking unsigned int (32bit)
	IPv6h = struct.unpack('!IHHHHHHHHHHHHHHHHHH', IPv6_header)
	IPv6Class.SourceAddress = read_IPv6address(IPv6_header[8:24])
	IPv6Class.DestinationAddress = read_IPv6address(IPv6_header[24:40])
	
	IPv6Class.Version = (IPv6h[0] >> 28) & 0xF
	IPv6Class.TrafficClass = (IPv6h[0] >> 20) & 0xFF
	IPv6Class.FlowLabel = IPv6h[0] & 0xFFFFF
	IPv6Class.PayloadLength = IPv6h[1]
	IPv6Class.NextHeader = (IPv6h[2] >> 8) & 0xFF
	IPv6Class.HopLimit = IPv6h[3] & 0xFF
	
	return IPv6Class
	
def read_IPv6address(IPv6_address_hex):
	#create IPv6_Address object
	IPv6AddressClass = _IPv6Address()
	
	IPv6h = struct.unpack('!QQ', IPv6_address_hex)
	IPv6_prefix = struct.unpack('!HHHHQ', IPv6_address_hex)

		#check address type
	if ((IPv6_prefix[0] >> 8) & 0xFF) == 0x0:
		IPv6AddressClass.TypeNumber = 1
		IPv6AddressClass.Type = "Loopback"
		IPv6AddressClass.Address = IPv6_address(IPv6_address_hex)

	elif ((IPv6_prefix[0] >> 12) & 0xE) == 0x2:
		IPv6AddressClass.TypeNumber = 2
		IPv6AddressClass.Type = "Global Unicast"
		IPv6AddressClass.GlobalRoutingPrefix = (IPv6h[0] >> 16) & 0xFFFFFFFFFFFF
		IPv6AddressClass.SubnetID = IPv6h[0] & 0xFFFF
		IPv6AddressClass.InterfaceID = IPv6h[1]
		IPv6AddressClass.Address = IPv6_address(IPv6_address_hex)

	elif ((IPv6_prefix[0] >> 4) & 0xFFC) == 0xFE8:
		IPv6AddressClass.TypeNumber = 3
		IPv6AddressClass.Type = "Link Local"
		IPv6AddressClass.InterfaceID = IPv6h[1]
		IPv6AddressClass.Address = IPv6_address(IPv6_address_hex)

	elif ((IPv6_prefix[0] >> 8) & 0xFE) == 0xFC:
		IPv6AddressClass.TypeNumber = 4
		IPv6AddressClass.Type = "Unique Local"
		IPv6AddressClass.LocalBit = (IPv6h[0] >> 120) & 0xFFFFFFFFFFFF
		IPv6AddressClass.GlobalID = (IPv6h[0] >> 16) & 0xFFFFFFFFFF
		IPv6AddressClass.SubnetID = IPv6[0] & 0xFFFF
		IPv6AddressClass.InterfaceID = IPv6[1]
		IPv6AddressClass.Address = IPv6_address(IPv6_address_hex)
	
	elif ((IPv6_prefix[0] >> 8) & 0xFF) == 0xFF:
		IPv6AddressClass.TypeNumber = 5
		IPv6AddressClass.Type = "Multicast"
		IPv6AddressClass.Flags = (IPv6h[0] >> 52) & 0xF
		IPv6AddressClass.Scope = (IPv6h[0] >> 48) & 0xF
		IPv6AddressClass.GroupID = (IPv6h[0] & 0xFFFFFFFFFFFF)*18446744073709551616
		IPv6AddressClass.GroupID += IPv6h[1]	
		IPv6AddressClass.Address = IPv6_address(IPv6_address_hex)			
			
	return IPv6AddressClass
        
def convert_transportprotocol(transport_protocol):
	#open the csv file with Datalink_protocols
	with open('Transport_protocols.csv') as csvfile:
		
		#read fine in dictionary
		reader = csv.DictReader(csvfile)
		
		#check compare transport_protocol code to codes from file
		for row in reader:
		
			#return protocol in text
			if int(row['hexcode'], 16) == transport_protocol:
				return row['abbreviation']

def extract_transportheader(packet, network_protocol, datalink_length, network_length):
	#we need the length of the previous headers combined
	combi_length = datalink_length + network_length

	if network_protocol == 6:
		TranClass = extract_TCPheader(packet, combi_length)
		return TranClass
	elif network_protocol == 17:
		TranClass = extract_UDPheader(packet, combi_length)
		return TranClass
	elif network_protocol == 1:
		TranClass = extract_ICMPheader(packet, combi_length)
		return TranClass
	else:
		print 'Transport protocol ' + str(network_protocol) + ' not supported.'
		return

#Transport Layer Protocols
def extract_TCPheader(packet, previous_length):
	#create _TCPHeader object
	TCPClass = _TCPHeader()

	#parse the TCP header
	TCP_header = packet[previous_length:TCPClass.Length + previous_length]

	#                                                       TCP HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|          Source Port          |       Destination Port        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                        Sequence Number                        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                    Acknowledgment Number                      |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|  Data |           |U|A|P|R|S|F|                               |
	#| Offset| Reserved  |R|C|S|S|Y|I|            Window             |
	#|       |           |G|K|H|T|N|N|                               |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|           Checksum            |         Urgent Pointer        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                    Options                    |    Padding    |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                             data                              |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	#unpacking the TCP header
	#H unpacking to unsigned short int
	#L unpacking to unsigned long int (32bit)
	#B unpacking to unsigned char
	TCPh = struct.unpack('!HHLLBBHHH', TCP_header)

	#extract info
	TCPClass.SourcePort = TCPh[0]
	TCPClass.DestinationPort = TCPh[1]
	TCPClass.Sequence = TCPh[2]
	TCPClass.Acknowledgement = TCPh[3]
	TCPClass.DataOffsetReserved = TCPh[4]

	#extract TCP length in bytes
	#options & padding may vary
	TCPClass.Length = TCPClass.DataOffsetReserved >> 4
	TCPClass.Length = TCPClass.Length * 4

	#extract data
	TCPClass.Data = packet[previous_length + TCPClass.Length:]

	return TCPClass

def extract_UDPheader(packet, previous_length):
	#create _UDPHeader object
	UDPClass = _UDPHeader()

	#parse the UDP header
	UDP_header = packet[previous_length:UDPClass.Length + previous_length]

	#                                                       UDP HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|          Source Port          |       Destination Port        |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|          Length               |       Checksum                |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+      
	#..............................DATA...............................

	#unpacking the UDP header
	UDPh = struct.unpack('!HHHH', UDP_header)

	#Extract info
	UDPClass.SourcePort = UDPh[0]
	UDPClass.DestinationPort = UDPh[1]
	UDPClass.Length = UDPh[2] #not sure if this includes DATA length or not
	UDPClass.Checksum = UDPh[3]

	#extract data
	UDPClass.Data = packet[previous_length + UDPClass.Length:]

	return UDPClass

def extract_ICMPheader(packet, previous_length):
	#create _ICMPHeader object
	ICMPClass = _ICMPHeader()

	#parse ICMP header
	ICMP_header = packet[previous_length:ICMPClass.Length + previous_length]

	#unpack ICMP header
	ICMPh = struct.unpack('!BBH' , ICMP_header)

	#                                                       ICMP HEADER
	#0                   1                   2                   3
	#0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|              Type     |              Code     |           Checksum            |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	#|                        Rest of header                             |
	#+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

	#extract info
	ICMPClass.Type = ICMPh[0]
	ICMPClass.Code = ICMPh[1]
	ICMPClass.Checksum = ICMPh[2]

	#extract data
	ICMPClass.Data = packet[ICMPClass.Length + previous_length:]

	return ICMPClass
        
#actual program code
#sock = create_socket()
#while True:
	#pack = extract_packet(sock)
	#pack.Length etc. to get values

	#print str(pack.Length)
	#print str(pack.DataLinkHeader.SourceMAC)
	#print str(pack.DataLinkHeader.DestinationMAC)
	#print str(pack.NetworkProtocol)
	#if pack.NetworkHeader.Protocol != None:
		#print str(pack.TransportProtocol)
