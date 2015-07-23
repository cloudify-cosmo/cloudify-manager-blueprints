#!/bin/bash

echo '
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCjM5GpakaKCpVJgt4biaTH4CP76qlJc0L5JkRFnhS9T7A9jYBFEaFgQwlw+cSZ0sq/KHa8kXwDRlUiRkSghA0MSs8r4JhPMhbpyiLzs20hCy6ahVFVLzgzjDOQsVODOZJ2JLBiyxPp6wJwBn2jdoKUl9dCrqm8h+6tAPP9naJXOwQCE+jSW6HyZhf9z8Z1kUlb4bZNHWwRR2AjUPip/ZZHHmEvr1xFZyOLK9g8X3UGibnS59oKqAMO5X5vXZYHWh923If0vBV31zessUPM07eTx/sYU4NVAc8jCDC/EZ/LR+KBTox25kh++8NTocWuosI2n0U/Kw9HsrZiixlQmLsd nir0s@nir0s-x1
' >> ~/.ssh/test_public_key.pub
cat ~/.ssh/test_public_key.pub >> ~/.ssh/authorized_keys