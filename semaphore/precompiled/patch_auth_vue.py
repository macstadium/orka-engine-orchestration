"""Patch Auth.vue: update background, swap login icon, add MacStadium logo."""

import re
import sys

path = sys.argv[1]
content = open(path).read()

content = content.replace(
    'background-image: url("../assets/background.svg");',
    "",
)
content = content.replace(
    "background-color: #005057;",
    "background: linear-gradient(135deg, #1e1e37 0%, #323151 100%);",
)
content = content.replace("background: #80808024;", "")

ms_logo = (
    "\n    <img\n"
    '      src="/macstadium-logo.png"\n'
    '      alt="MacStadium"\n'
    '      :style="{\n'
    "        position:'absolute',bottom:'28px',left:'50%',\n"
    "        transform:'translateX(-50%)',width:'110px',\n"
    "        opacity:'0.45',zIndex:'1'\n"
    '      }"\n'
    "    />"
)
content = content.replace(
    '<v-dialog v-model="loginHelpDialog"',
    ms_logo + '\n    <v-dialog v-model="loginHelpDialog"',
)

content = re.sub(r"[ \t]+$", "", content, flags=re.MULTILINE)
open(path, "w").write(content)
