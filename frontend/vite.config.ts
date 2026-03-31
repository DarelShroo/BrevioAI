import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { AntDesignVueResolver } from 'unplugin-vue-components/resolvers';
import { fileURLToPath, URL } from 'url';
import vueDevTools from 'vite-plugin-vue-devtools';

const isVitest = process.env.VITEST === 'true';

const plugins = [
  vue(),
  Components({
    resolvers: [
      AntDesignVueResolver({
        importStyle: false,
      }),
    ],
  }),
];

if (!isVitest) {
  plugins.push(vueDevTools());
}

export default defineConfig({
  plugins,

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
    extensions: ['.ts', '.js', '.vue'],
  },
  server: {
    port: 80
  }
});
