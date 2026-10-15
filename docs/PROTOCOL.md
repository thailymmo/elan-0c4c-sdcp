# ELAN 04f3:0c4c firmware 3.05: protocol notes

The sensor reports itself as `ELAN:ARM-M4`, USB vendor class, with bulk endpoints
`0x01` (commands out), `0x83` (replies) and `0x84` (replies to commands that wait
for a finger). Every command starts with `40 ff <code>`; every reply starts with
`40 <status>`.

Firmware 3.04 works with the community `elanmoc2` driver. Firmware 3.05 only
commits templates inside a Microsoft **SDCP** (Secure Device Connection Protocol)
session: without it, enrollment stages pass and the template counter increases,
but identification always answers `0xfd` (no match), `0x12` (finger info) answers
`0xff`, and templates are gone after a power cycle.

The SDCP command layout below was worked out from the vendor's Windows driver
(`WbfUsbDriver.dll` 3.2.12011.10039, Microsoft Update Catalog) and confirmed on
real hardware. The model certificate is `CN=Secure BIO Sensor`, issued by
`Windows Hello 5CF190F8 CA 2018`.

| Code | Name | Payload | Reply (after `40 <status>`) |
|------|------|---------|------------------------------|
| `01` | enroll stage | `count, 08, stage, 00` | on `0x84`; `00` ok, `41`-`44` move finger, `fb` dirty, `fe` too little area |
| `02` | abort finger wait | - | 2 bytes |
| `03` | identify (wait for finger) | - | on `0x84`; slot index on match, `fd` no match |
| `04` | enrolled count | - | count |
| `05` | delete (2-byte arg) | `H L` | deletes a template even with a wrong argument; **do not use** |
| `06` | SDCP connect | `r_h(32) pk_h(65)` | `r_d(32) pk_d(65) pk_f(65) h_f(32) mac(32) s_m(64) s_d(64) cert_m(846)` |
| `07` | SDCP reconnect | `r(32)` | `mac(32)` |
| `09` | SDCP enrollment nonce | - | `nonce(32)` |
| `0a` | SDCP enroll commit | `id(32)`, `id = HMAC(s, "enroll\0" + nonce)` | - |
| `0c` | SDCP authorized identity | `nonce(32)` | `id(32) mac(32)`, `mac = HMAC(s, "identify\0" + nonce + id)` |
| `0d` | application key (Windows only) | - | 64 bytes |
| `14` | set mode | `mode` | - |
| `99` | wipe all templates | - | no reply; sensor busy ~5 s |

The key schedule is standard SDCP: ECDH(P-256) with `pk_f`, then KBKDF-HMAC-SHA256
`"master secret"` (context `r_h || r_d`) and `"application keys"`; the first 32
bytes are the application secret `s`. The connect MAC is
`HMAC(s, "connect\0" + SHA256(cert_m || pk_d || pk_f || h_f || s_m || s_d))`
over the full 846-byte `cert_m` field.

Template storage is shared by every OS on the machine (about 10 slots), including
Windows Hello. Wiping the sensor removes prints enrolled by other systems.
