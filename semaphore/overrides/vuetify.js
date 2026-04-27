// MacStadium-branded Vuetify 2 plugin.
// Based on the upstream web/src/plugins/vuetify.js; adds a theme block so that
// the MacStadium palette is applied across the compiled CSS bundle.
//
// Style guide colours:
//   Orange    #FE9000  – primary actions
//   Storm     #323151  – nav / sidebar (light mode)
//   Navy      #1e1e37  – nav / sidebar (dark mode)
//   Blue      #5366CC  – secondary
//   Hi-blue   #5f78ff  – links / accent

import Vue from 'vue';
import Vuetify from 'vuetify/lib';
import OpenTofuIcon from '@/components/OpenTofuIcon.vue';
import PulumiIcon from '@/components/PulumiIcon.vue';
import TerragruntIcon from '@/components/TerragruntIcon.vue';
import HashicorpVaultIcon from '@/components/HashicorpVaultIcon.vue';
import DvlsIcon from '../components/DvlsIcon.vue';

Vue.use(Vuetify);

export default new Vuetify({
  theme: {
    themes: {
      light: {
        primary: '#FE9000',
        secondary: '#323151',
        accent: '#5f78ff',
        anchor: '#5f78ff',
        info: '#5366CC',
      },
      dark: {
        primary: '#FE9000',
        secondary: '#1e1e37',
        accent: '#5f78ff',
        anchor: '#5f78ff',
        info: '#5366CC',
      },
    },
  },
  icons: {
    values: {
      tofu: { component: OpenTofuIcon },
      pulumi: { component: PulumiIcon },
      terragrunt: { component: TerragruntIcon },
      hashicorp_vault: { component: HashicorpVaultIcon },
      dvls: { component: DvlsIcon },
    },
  },
});
