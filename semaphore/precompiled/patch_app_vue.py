"""Patch App.vue: add Orka logo to nav drawer."""

import sys

path = sys.argv[1]
content = open(path).read()
content = content.replace(
    '<v-menu bottom max-width="235"',
    '<v-img src="/orka-logo.png" max-width="160" contain class="mt-4 mb-2 mx-auto" />\n      '
    + '<v-menu bottom max-width="235"',
)
open(path, "w").write(content)
