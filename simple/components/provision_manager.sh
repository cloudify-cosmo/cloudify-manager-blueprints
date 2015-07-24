#!/bin/bash

function update_local_cache() {
    sudo yum -y update
}

function suppress_pip_ssl_err() {
    sudo yum install -y libssl-dev
    curl --show-error --silent --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python
    sudo pip install requests[security]
}

update_local_cache
# suppress_pip_ssl_err

echo '
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAozORqWpGigqVSYLeG4mkx+Aj++qpSXNC+SZERZ4UvU+wPY2A
RRGhYEMJcPnEmdLKvyh2vJF8A0ZVIkZEoIQNDErPK+CYTzIW6coi87NtIQsumoVR
VS84M4wzkLFTgzmSdiSwYssT6esCcAZ9o3aClJfXQq6pvIfurQDz/Z2iVzsEAhPo
0luh8mYX/c/GdZFJW+G2TR1sEUdgI1D4qf2WRx5hL69cRWcjiyvYPF91Bom50ufa
CqgDDuV+b12WB1ofdtyH9LwVd9c3rLFDzNO3k8f7GFODVQHPIwgwvxGfy0figU6M
duZIfvvDU6HFrqLCNp9FPysPR7K2YosZUJi7HQIDAQABAoIBABZ4ICLiFeolgN5J
HUlPTxeRvYKOkVYif2MMKLQpCpPx58Lhu3pG7h/xutgKG05OXkmpSYe2xAszYL9C
S2qKI73Agvt4hZ/Jtqvjf6Jr3qeBAZ6WolcHFEbMk8DlGSllAMwxSvOfIBPBnmlM
C3o488t/iEyO/aGOWYcKLY2KaXJ23jw+42KpxXxKYnxDtC8TLw2YZTWCoSgtrVpD
qV2/JDheitmCDBzAXNZLZ4gL6FXytgSeVaEhHq7XXiqxsHdrPo+EMHmH/d4CRO9n
m+LfJnp8zFcGwcekcyovUmH6EF8NoLlD+Hm+7+QI15EvBbAX8ZCCCeR4y/rULslM
HyME/GUCgYEA2CbZ8n+Hd+f9S1b9cOHnBQYCbcbrJMmZ4UAxucPkRrs2lMJDXOHC
5duVlfBvRykI7prrDtURmrQH3+kIk0gNAWBhnNvRf4u2vXhjzbyU7L2ZTydQFmRZ
IwH+pyAPJzkAeY+a3ibyGsAgXIa9svBYX/P8sjv0eA8kQKhlbkOucYsCgYEAwUnC
jiBLPK3kZNlC9Unqf1O0BYptq5vOIv39aJDMZTVK7IPA5bChKPvt0diJfYJmRFuH
Cw+31clfejT3JtyW21Xewmt+a6XuSfsz6w5CGhb52RYQe21DDLBqTFRLLaqJd1Tt
Xk++Vszv5bxVVm972Ie0IAj0BG9lE31nynRFSvcCgYBhxik+TTutHI5yHvZjsnv6
xL4ihCFnsZ3ey1fy7M58xECrR7iK8kBkE1D10x2y9bfpnsAHJJBjB16shU/wt13S
qpNdDf4VENDnoeabcNt4v0bzDBhpGJlNgaB8Xr8cAefaFQB7zugi+5dn4zc6EwgW
11oOEZrDGC5Q5RuEpi7pgwKBgQC2pyg2PKg8iCsbbgALYbU6a3PkBINMtuheQtx0
MtkkDu9lf8AKjhZNb3y2X8TVmSNhF4kO1+SmHyydhG3GCJB6ZrQhz4jg2yXKPZs7
Vfb7RpkGHwamTIMe+5sH1GRSnCRZYyUIiZzZ08IjvAx8qM9EuEBsQWmuw0Gl4Ezz
kVpl0wKBgQCeC/9yjnXr8mv/XkOulCEcl6tt6gbccW6ec1KLODGi5FkiJnytChqL
9MPOIWhGsNjxWCBTypvEyI10drcwbMXgy5B5e1u1YFeUSj/jlQyo9E/NNneLNKd0
MVC41Sc/qvK46/g9auXpq+JikdMowHZoYhRBAPlZdh+Mw4jP7OuP0Q==
-----END RSA PRIVATE KEY-----
' >> ~/.ssh/test_private_key

echo '
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCjM5GpakaKCpVJgt4biaTH4CP76qlJc0L5JkRFnhS9T7A9jYBFEaFgQwlw+cSZ0sq/KHa8kXwDRlUiRkSghA0MSs8r4JhPMhbpyiLzs20hCy6ahVFVLzgzjDOQsVODOZJ2JLBiyxPp6wJwBn2jdoKUl9dCrqm8h+6tAPP9naJXOwQCE+jSW6HyZhf9z8Z1kUlb4bZNHWwRR2AjUPip/ZZHHmEvr1xFZyOLK9g8X3UGibnS59oKqAMO5X5vXZYHWh923If0vBV31zessUPM07eTx/sYU4NVAc8jCDC/EZ/LR+KBTox25kh++8NTocWuosI2n0U/Kw9HsrZiixlQmLsd nir0s@nir0s-x1
' >> ~/.ssh/test_public_key.pub

cat ~/.ssh/test_public_key.pub >> ~/.ssh/authorized_keys
