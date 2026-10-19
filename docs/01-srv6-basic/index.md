# 01. SRv6 基本設定

## 1.1 IPv6 アドレス設定

!!! abstract "ゴール"

```
全てのルータのループバックに IPv6 アドレスを設定し、コア向けインタフェースで IPv6 を有効化します。また、他のルータのループバックを学習していないことを確認します。
```

ループバックに IPv6 アドレスを設定し、コア向けインタフェースで IPv6 を有効化します。（PE1 ~ P5）

- ループバックアドレスは、ルータ番号に応じて `fcbb:bb00:N::1/128` に変更してください。
- コア向けインタフェース（IPv4 アドレス `10.XY.0.N` が設定されているインタフェース）には `ipv6 enable` を設定してください。設定対象のインタフェースはルータに応じて変更してください。
- SRv6 では、コア向けインタフェースにグローバル IPv6 アドレスを設定する必要はありません。IS-IS のアジャセンシーやネクストホップ、uA SID はリンクローカルアドレスで動作し、SRv6 の転送は Locator 宛の経路で行われるためです。`ipv6 enable` により、リンクローカルアドレスのみが自動で付与されます。

```
interface Loopback0
 ipv6 address fcbb:bb00:1::1/128
 ipv4 address 1.1.1.1/32
!
interface GigabitEthernet0/0/0/0
 no shut
 ipv6 enable
!
interface GigabitEthernet0/0/0/1
 no shut
 ipv6 enable
!
```

IPv6 が有効になったことを確認します。コア向けインタフェースにはリンクローカルアドレスのみが付与されています。（PE1 ~ P5）

```
RP/0/RP0/CPU0:PE1#show ipv6 int brief
Sun Oct 18 18:17:45.595 UTC
Loopback0              [Up/Up]
    fe80::c154:6aff:feac:a052                     
    fcbb:bb00:1::1                                
MgmtEth0/RP0/CPU0/0    [Shutdown/Down]
    unassigned                                    
GigabitEthernet0/0/0/0 [Up/Up]
    fe80::5054:ff:fe3a:1b61                       
GigabitEthernet0/0/0/1 [Up/Up]
    fe80::5054:ff:fe4a:db0                        
GigabitEthernet0/0/0/2 [Shutdown/Down]
    unassigned     
```

他のルータのループバックを学習していないことを確認します。コア向けインタフェースにはグローバル IPv6 アドレスがないため、ルーティングテーブルには自身のループバックのみが表示されます。（PE1 ~ P5）

```
RP/0/RP0/CPU0:PE1#show route ipv6
Sun Oct 18 18:18:02.550 UTC
(--- omitted ---)
Gateway of last resort is not set

L    fcbb:bb00:1::1/128 is directly connected,
      00:06:38, Loopback0
RP/0/RP0/CPU0:PE1#
```



## 1.2 IS-IS 設定

!!! abstract "ゴール"

```
IS-IS (IPv6) を設定し、全てのノード間で IPv6 ループバックによる疎通を確立します。
```

IS-IS の設定を行います。（PE1 ~ P5）

- NET は、ルータ番号に応じて `49.0001.0000.0000.000N.00` に変更してください。
- IS-IS を有効にするインタフェースは、ルータに応じて変更してください。
- 今回は IPv6 のアドレスファミリのみを有効にし、コア網を IPv6 のみで構成します。
- `router-id Loopback0` は、03 以降の SRv6-TE で使用する IPv6 TE Router ID の設定です。

```
router isis core
 is-type level-2-only
 net 49.0001.0000.0000.0001.00
 address-family ipv6 unicast
  metric-style wide
  router-id Loopback0
 !
 interface Loopback0
  passive
  address-family ipv6 unicast
  !
 !
 interface FourHundredGigE0/0/0/0
  point-to-point
  address-family ipv6 unicast
  !
 !
 interface FourHundredGigE0/0/0/1
  point-to-point
  address-family ipv6 unicast
  !
 !
!
```

IS-IS のアジャセンシーを確認します。（PE1 ~ P5）

```
RP/0/RP0/CPU0:PE1#show isis adjacency 
Sun Oct 18 18:20:22.216 UTC

IS-IS core Level-2 adjacencies:
System Id      Interface                SNPA           State Hold Changed  NSF IPv4 IPv6
                                                                               BFD  BFD 
P4             Gi0/0/0/0                *PtoP*         Up    27   00:00:22 Yes None None
P5             Gi0/0/0/1                *PtoP*         Up    29   00:00:09 Yes None None

Total adjacency count: 2
RP/0/RP0/CPU0:PE1#
```

ルーティングテーブルの確認を行います。（PE1 ~ P5）

他のルータのループバックが IS-IS で学習されていることがわかります。IS-IS で学習した経路のネクストホップは、隣接ルータのリンクローカルアドレスとなります。

```
RP/0/RP0/CPU0:PE1#show route ipv6 isis
Sun Oct 18 18:20:34.385 UTC

i L2 fcbb:bb00:2::1/128 
      [115/20] via fe80::5054:ff:fec1:f132, 00:00:24, GigabitEthernet0/0/0/0
i L2 fcbb:bb00:3::1/128 
      [115/20] via fe80::5054:ff:febb:bec1, 00:00:10, GigabitEthernet0/0/0/1
i L2 fcbb:bb00:4::1/128 
      [115/10] via fe80::5054:ff:fec1:f132, 00:00:31, GigabitEthernet0/0/0/0
i L2 fcbb:bb00:5::1/128 
      [115/10] via fe80::5054:ff:febb:bec1, 00:00:17, GigabitEthernet0/0/0/1
RP/0/RP0/CPU0:PE1#
```

他のルータの IPv6 ループバックに疎通できることを確認します。（PE1 ~ P5）

```
RP/0/RP0/CPU0:PE1#ping ipv6 fcbb:bb00:2::1 source fcbb:bb00:1::1
Sun Oct 18 18:20:47.318 UTC
Type escape sequence to abort.
Sending 5, 100-byte ICMP Echos to fcbb:bb00:2::1, timeout is 2 seconds:
!!!!!
Success rate is 100 percent (5/5), round-trip min/avg/max = 3/4/9 ms
RP/0/RP0/CPU0:PE1#
```



## 1.3 SRv6 設定

!!! abstract "ゴール"

```
SRv6 (uSID) を設定し、各ルータの SRv6 Locator と SID が IS-IS により広報されることを確認します。
```

SRv6 SID が何も割り当てられていないことを確認します。（PE1 ~ PE3）

```
RP/0/RP0/CPU0:PE1#show segment-routing srv6 sid
Sun Oct 18 18:20:59.157 UTC
RP/0/RP0/CPU0:PE1#
```

SRv6 の有効化と Locator の設定を行います。（PE1 ~ PE3）

- Locator のプレフィックスは、ルータ番号に応じて `fcbb:bb00:N::/48` に変更してください。
- `micro-segment behavior unode psp-usd` により、uSID (F3216) の Locator として動作します。
- `encapsulation source-address` には、SRv6 でカプセル化する際の Outer IPv6 ヘッダの送信元アドレスとして、自身のループバックアドレスを指定します。
- Pルータには設定不要です。

```
segment-routing
 srv6
  encapsulation
   source-address fcbb:bb00:1::1
  !
  locators
   locator MAIN
    micro-segment behavior unode psp-usd
    prefix fcbb:bb00:1::/48
   !
  !
 !
!
router isis core
 address-family ipv6 unicast
  segment-routing srv6
   locator MAIN
   !
  !
 !
!
```

Locator の状態を確認します。（PE1 ~ PE3）

```
RP/0/RP0/CPU0:PE1#show segment-routing srv6 locator
Sun Oct 18 18:21:58.108 UTC
Name                  ID       Algo  Prefix                    Status   Flags   
--------------------  -------  ----  ------------------------  -------  --------
MAIN                  1        0     fcbb:bb00:1::/48          Up       U       
RP/0/RP0/CPU0:PE1#
```

自身に割り当てられた SRv6 SID を確認します。（PE1 ~ PE3）

Node SID に相当する uN SID と、IS-IS が有効なインタフェースごとに Adjacency SID に相当する uA SID が自動で割り当てられていることがわかります。

```
RP/0/RP0/CPU0:PE1#show segment-routing srv6 sid
Sun Oct 18 18:22:11.288 UTC

*** Locator: 'MAIN' *** 

SID                         Behavior          Identification                    Owner               State  RW
--------------------------  ----------------  --------------------------------  ------------------  -----  --
fcbb:bb00:1::               uN (PSP/USD)      'default':1                       sidmgr              InUse  Y 
fcbb:bb00:1:e000::          uA (PSP/USD)      [Gi0/0/0/0, Link-Local]:0         isis-core           InUse  Y 
fcbb:bb00:1:e001::          uA (PSP/USD)      [Gi0/0/0/1, Link-Local]:0         isis-core           InUse  Y 
RP/0/RP0/CPU0:PE1#
```

ルーティングテーブルにて、他ルータの Locator (/48) が IS-IS で学習されていること、及び自身の SID がローカルの SRv6 Endpoint として登録されていることを確認します。（PE1 ~ PE3）

```
RP/0/RP0/CPU0:PE1#show route ipv6
Sun Oct 18 18:22:33.912 UTC
(--- omitted ---)

Gateway of last resort is not set

s    fcbb:bb00:1::/48, SRv6 Endpoint uN (shift) 
      [0/0] via ::, 00:01:17
s    fcbb:bb00:1::/64, SRv6 Endpoint uN (PSP/USD) 
      [0/0] via ::, 00:01:17
L    fcbb:bb00:1::1/128 is directly connected,
      00:11:10, Loopback0
s    fcbb:bb00:1:1::/64 
      [0/0] via ::, 00:01:17, Null0
s    fcbb:bb00:1:e000::/64, SRv6 Endpoint uA (shift) 
      [0/0] via fe80::5054:ff:fec1:f132, 00:01:17, GigabitEthernet0/0/0/0
s    fcbb:bb00:1:e000::/80, SRv6 Endpoint uA (PSP/USD) 
      [0/0] via fe80::5054:ff:fec1:f132, 00:01:17, GigabitEthernet0/0/0/0
s    fcbb:bb00:1:e001::/64, SRv6 Endpoint uA (shift) 
      [0/0] via fe80::5054:ff:febb:bec1, 00:01:17, GigabitEthernet0/0/0/1
s    fcbb:bb00:1:e001::/80, SRv6 Endpoint uA (PSP/USD) 
      [0/0] via fe80::5054:ff:febb:bec1, 00:01:17, GigabitEthernet0/0/0/1
i L2 fcbb:bb00:2::/48 
      [115/21] via fe80::5054:ff:fec1:f132, 00:00:55, GigabitEthernet0/0/0/0
i L2 fcbb:bb00:2::1/128 
      [115/20] via fe80::5054:ff:fec1:f132, 00:01:15, GigabitEthernet0/0/0/0
i L2 fcbb:bb00:3::/48 
      [115/21] via fe80::5054:ff:febb:bec1, 00:00:44, GigabitEthernet0/0/0/1
i L2 fcbb:bb00:3::1/128 
      [115/20] via fe80::5054:ff:febb:bec1, 00:01:15, GigabitEthernet0/0/0/1
i L2 fcbb:bb00:4::1/128 
      [115/10] via fe80::5054:ff:fec1:f132, 00:01:15, GigabitEthernet0/0/0/0
i L2 fcbb:bb00:5::1/128 
      [115/10] via fe80::5054:ff:febb:bec1, 00:01:15, GigabitEthernet0/0/0/1
s    fcbb:bb00:e000::/48, SRv6 Endpoint uA (shift) 
      [0/0] via fe80::5054:ff:fec1:f132, 00:01:17, GigabitEthernet0/0/0/0
s    fcbb:bb00:e000::/64, SRv6 Endpoint uA (PSP/USD) 
      [0/0] via fe80::5054:ff:fec1:f132, 00:01:17, GigabitEthernet0/0/0/0
s    fcbb:bb00:e001::/48, SRv6 Endpoint uA (shift) 
      [0/0] via fe80::5054:ff:febb:bec1, 00:01:17, GigabitEthernet0/0/0/1
s    fcbb:bb00:e001::/64, SRv6 Endpoint uA (PSP/USD) 
      [0/0] via fe80::5054:ff:febb:bec1, 00:01:17, GigabitEthernet0/0/0/1
RP/0/RP0/CPU0:PE1#
```

P4 でルーティングテーブルを確認すると、PE3 の Locator 向けのルートがECMPになっていることがわかります。

SR-MPLS ではラベル (Prefix SID) ごとに LFIB エントリが作られていましたが、SRv6 では Locator のプレフィックス (/48) に対する通常の IPv6 ルーティングで転送されます。

```
RP/0/RP0/CPU0:P4#show route ipv6 fcbb:bb00:3::/48
Sun Oct 18 18:24:09.577 UTC

Routing entry for fcbb:bb00:3::/48
  Known via "isis core", distance 115, metric 21, SRv6-locator, type level-2
  Installed Oct 18 18:21:49.568 for 00:02:20
  Routing Descriptor Blocks
    fe80::5054:ff:fe62:869a, from fcbb:bb00:3::1, via GigabitEthernet0/0/0/1
      Route metric is 21
    fe80::5054:ff:fe3f:fcba, from fcbb:bb00:3::1, via GigabitEthernet0/0/0/2
      Route metric is 21
  No advertising protos. 
RP/0/RP0/CPU0:P4#
```

Traceroute 確認を実施します。（PE1 ~ PE3）

下記の例では、PE1 から PE2 (fcbb:bb00:2::1) 宛に Traceroute を実施しており、Next Hopである PE4 を経由して転送されていることがわかります。SR-MPLS と異なりラベルは付与されず、通常の IPv6 パケットとして転送されます。

なお、コア向けインタフェースにはグローバル IPv6 アドレスがないため、各ホップからの応答 (ICMPv6 Time Exceeded) の送信元には、各ルータのループバックアドレスが使用されます。

```
RP/0/RP0/CPU0:PE1#traceroute ipv6 fcbb:bb00:2::1
Sun Oct 18 18:24:28.061 UTC

Type escape sequence to abort.
Tracing the route to fcbb:bb00:2::1

 1  fcbb:bb00:4::1 6 msec 2 msec 2 msec
 2  fcbb:bb00:2::1 5 msec 4 msec 4 msec
RP/0/RP0/CPU0:PE1#
```



## 1.4 SRv6 の動作確認（オプション）

!!! abstract "ゴール"

```
SRv6 Manager 及び IS-IS データベースを確認し、uSID のフォーマットと Locator / SID がどのように広報されるかを理解します。
```

SRv6 Manager にて、SRv6 の動作状況や SID フォーマットを確認します。（PE1 ~ PE3）

uSID Block が `fcbb:bb00::/32`、SID フォーマットが F3216 (Block 32 bit / uSID 16 bit) で動作していることがわかります。また、動的に割り当てられる SID の Function は `0xe000` から始まる LIB (Local ID Block) から払い出されます。

```
RP/0/RP0/CPU0:PE1#show segment-routing srv6 manager
Sun Oct 18 18:24:43.090 UTC
Parameters:
  SRv6 Enabled: Yes
  SRv6 Operational Mode: 
    Micro-segment:
      SID Base Block: fcbb:bb00::/24
  Encapsulation:
    Source Address:
      Configured: fcbb:bb00:1::1
      Default: fcbb:bb00:1::1
    Hop-Limit: Default 
    Traffic-class: Default 
  SID Formats:
    f3216 <32B/16NFA> (2)
      uSID LIB Range:
        LIB Start   : 0xe000
        ELIB Start  : 0xfe00
      uSID WLIB Range:
        EWLIB Start : 0xfff7
Summary:
  Number of Locators: 1 (1 operational)
  Number of SIDs: 2 (0 stale)
  Max SID resources: 9000
  Number of free SID resources: 8998
  OOR:    
    Thresholds (resources): Green 450, Warning 270
    Status: Resource Available
        History: (0 cleared, 0 warnings, 0 full)
    Block fcbb:bb00::/32:
        Number of SIDs free: 7678
        Max SIDs: 7680
        Thresholds: Green 384, Warning 231
        Status: Resource Available
            History: (0 cleared, 0 warnings, 0 full)
Platform Capabilities:
  SRv6: Yes
  TILFA: Yes
  Microloop-Avoidance: Yes
  Endpoint behaviors: 
    End.DX6
    End.DX4
    End.DT6
    End.DT4
    End.DT46
    End.DX2
    End.DT2U
    End.DT2M
    End (PSP/USD)
    End.X (PSP/USD)
    uN (shift)
    uN (PSP/USD)
    uA (shift)
    uA (PSP/USD)
    uDX6
    uDX4
    uDT6
    uDT4
    uDT46
    uDX2
    uDT2U
    uDT2M
    uB6 (Insert.Red)
    uB6 (Encaps.Red)
    uB6 (PSP/USD Insert.Red)
    uB6 (PSP/USD Encaps.Red)
    uTEF
    uB6 (shift)
  Headend behaviors: 
    T
    H.Insert.Red
    H.Encaps.Red
    H.Encaps.L2.Red
  Security rules: 
    SEC-1
    SEC-2
    SEC-3
  Counters: 
    CNT-3
  Signaled parameters: 
    Max-SL          : 255
    Max-End-Pop-SRH : 255
    Max-H-Insert    : 10 sids
    Max-H-Encap     : 10 sids
    Max-End-D       : 255
  Configurable parameters (under srv6): 
    Ranges: 
      LIB           : Yes
      WLIB          : Yes
    Encapsulation: 
      Source Address: Yes
      Hop-Limit     : value=Yes, propagate=Yes
      Traffic-class : value=Yes, propagate=Yes
    Endpoint Dual-SID Termination: Yes
  Default parameters (under srv6): 
    Encapsulation: 
      Hop-Limit     : value=0, propagate=No
      Traffic-class : value=0, propagate=No
  Max Locators: 16
  Max SIDs: 9000
  SID Holdtime: 3 mins
RP/0/RP0/CPU0:PE1#
```

IS-IS での Locator 及び SID の広報を確認します。（PE1 ~ PE3）

SR-MPLS では Prefix SID (Index) や SRGB を IGP で広報していましたが、SRv6 では Locator のプレフィックスと、uN / uA SID 及びその SID 構造 (SID Structure) が広報されます。SRGB のようなラベル空間の設定・調整は不要です。

```
RP/0/RP0/CPU0:PE1#show isis database PE1.00-00 verbose
Sun Oct 18 18:25:16.588 UTC

IS-IS core (Level-2) Link State Database
LSPID                 LSP Seq Num  LSP Checksum  LSP Holdtime/Rcvd  ATT/P/OL
PE1.00-00           * 0x00000005   0xd767        961  /*            0/0/0
  Area Address:   49.0001
  LSP MTU:        1492
  NLPID:          0x8e
  MT:             IPv6 Unicast                                 0/0/0
  IPv6 Router ID: fcbb:bb00:1::1
  IPv6 Address:   fcbb:bb00:1::1
  Hostname:       PE1
  Router Cap:     0.0.0.0 D:0 S:0
    IPv6 Router ID: fcbb:bb00:1::1
    SR Algorithm: 
      Algorithm: 0
      Algorithm: 1
    SRv6: O:0
    Node Maximum SID Depth: 
      SRH Max SL:       255
      SRH Max End Pop:  255
      SRH Max T.insert: 10
      SRH Max T.encaps: 10
      SRH Max End D:    255
  SRv6 Locator:   MT (IPv6 Unicast) fcbb:bb00:1::/48 D:0 Metric: 1 Algorithm: 0
    Prefix Attribute Flags: X:0 R:0 N:0 E:0 A:0
    END SID: fcbb:bb00:1:: uN (PSP/USD)
      SID Structure:
        Block Length: 32, Node-ID Length: 16, Func-Length: 0, Args-Length: 80
  Metric: 10         MT (IPv6 Unicast) IS-Extended P4.00
    Local Interface ID: 3, Remote Interface ID: 4
    Physical BW: 1000000 kbits/sec, 125000000 bytes/sec
    END.X SID: fcbb:bb00:1:e000:: B:0 S:0 P:0 uA (PSP/USD) Alg:0
      SID Structure:
        Block Length: 32, Node-ID Length: 16, Func-Length: 16, Args-Length: 64
  Metric: 10         MT (IPv6 Unicast) IS-Extended P5.00
    Local Interface ID: 4, Remote Interface ID: 4
    Physical BW: 1000000 kbits/sec, 125000000 bytes/sec
    END.X SID: fcbb:bb00:1:e001:: B:0 S:0 P:0 uA (PSP/USD) Alg:0
      SID Structure:
        Block Length: 32, Node-ID Length: 16, Func-Length: 16, Args-Length: 64
  Metric: 1          MT (IPv6 Unicast) IPv6 fcbb:bb00:1::/48
    Prefix Attribute Flags: X:0 R:0 N:0 E:0 A:0
  Metric: 0          MT (IPv6 Unicast) IPv6 fcbb:bb00:1::1/128
    Prefix Attribute Flags: X:0 R:0 N:1 E:0 A:0
    Source Router ID: fcbb:bb00:1::1
RP/0/RP0/CPU0:PE1# 
```

