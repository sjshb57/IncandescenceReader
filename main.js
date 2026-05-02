const { app, BrowserWindow, protocol } = require('electron');
const path = require('path');
const fs   = require('fs');

// ── 数据根目录解析
//    打包后：resources/ 目录是数据所在的位置（accounts/ 或 wayback_snapshots/ 都在这里）
//    开发时：项目根目录（同 main.js 所在目录）
function getDataBaseDir() {
  if (app.isPackaged) {
    return process.resourcesPath;
  }
  return __dirname;
}

// ── 注册自定义协议 incr://，让 Reader.html 通过它读取本地文件
// 这样完全绕开 file:// 的跨域限制，fetch() 正常工作
//
// URL 路由规则：
//   incr://local/_accounts                      → 动态扫描 accounts/ 下所有子目录，
//                                                  读取每个的 profile.json 合成账号清单 JSON
//   incr://local/accounts/AnIncandescence/...   → DATA/accounts/AnIncandescence/...
//   incr://local/wayback_snapshots/...          → DATA/wayback_snapshots/... (向后兼容旧目录)
//   incr://local/Reader.html / 其他静态资源      → __dirname/...
function registerProtocol() {
  // _accounts 是虚拟路径，用 buffer 协议返回动态生成的 JSON
  protocol.registerBufferProtocol('incr', (request, callback) => {
    let urlPath = request.url.replace('incr://local/', '');
    // 解码 URI
    urlPath = decodeURIComponent(urlPath);

    const dataBase = getDataBaseDir();

    // 虚拟路径：扫 accounts/ 下所有子目录，组合 profile.json 生成账号清单
    if (urlPath === '_accounts' || urlPath === '_accounts.json') {
      const accountsDir = path.join(dataBase, 'accounts');
      let list = [];
      try {
        if (fs.existsSync(accountsDir)) {
          const dirs = fs.readdirSync(accountsDir, { withFileTypes: true })
            .filter(d => d.isDirectory() && !d.name.startsWith('.'))
            .map(d => d.name);

          for (const dir of dirs) {
            const profilePath = path.join(accountsDir, dir, 'wayback_snapshots', 'profile.json');
            if (!fs.existsSync(profilePath)) continue;
            try {
              const prof = JSON.parse(fs.readFileSync(profilePath, 'utf8'));
              list.push({
                dir: dir,
                name:     prof.name     || dir,
                username: prof.username || dir,
                bio:      prof.bio      || '',
                avatar:   prof.avatar   ? `accounts/${dir}/wayback_snapshots/${prof.avatar}` : '',
                banner:   prof.banner   ? `accounts/${dir}/wayback_snapshots/${prof.banner}` : '',
              });
            } catch (e) {
              // 跳过坏掉的 profile.json
              console.error(`[incr] 解析 ${profilePath} 失败:`, e.message);
            }
          }
        }
      } catch (e) {
        console.error('[incr] 扫描 accounts/ 失败:', e);
      }
      callback({
        mimeType: 'application/json',
        data: Buffer.from(JSON.stringify(list), 'utf8'),
      });
      return;
    }

    // 实文件路径
    let filePath;
    if (urlPath.startsWith('accounts/')) {
      filePath = path.join(dataBase, urlPath);
    } else if (urlPath.startsWith('wayback_snapshots/')) {
      filePath = path.join(dataBase, urlPath);
    } else {
      filePath = path.join(__dirname, urlPath);
    }

    // buffer 协议下读文件
    try {
      const buf = fs.readFileSync(filePath);
      // 简单判 mime
      const ext = path.extname(filePath).toLowerCase();
      const mimeMap = {
        '.html': 'text/html', '.htm': 'text/html',
        '.js':   'application/javascript', '.css': 'text/css',
        '.json': 'application/json',
        '.png':  'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif':  'image/gif', '.webp': 'image/webp', '.svg': 'image/svg+xml',
        '.mp4':  'video/mp4', '.webm': 'video/webm',
        '.txt':  'text/plain',
      };
      callback({
        mimeType: mimeMap[ext] || 'application/octet-stream',
        data: buf,
      });
    } catch (e) {
      callback({ statusCode: 404 });
    }
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width:  1440,
    height: 900,
    minWidth:  900,
    minHeight: 600,
    title: '白炽阅读器 · IncandescenceReader',
    backgroundColor: '#000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      // 允许 incr:// 协议页面访问本地资源
      webviewTag: false,
    },
    // 无边框可选，保留系统标题栏更稳定
    frame: true,
    show: false, // 加载完再显示，避免白屏闪烁
  });

  win.once('ready-to-show', () => win.show());

  win.loadURL('incr://local/Reader.html');

  // 开发时打开 DevTools（打包后注释掉）
  // win.webContents.openDevTools();
}

// 必须在 app ready 之前调用，否则新版 Electron 中自定义协议权限不生效
protocol.registerSchemesAsPrivileged([
  { scheme: 'incr', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }
]);

app.whenReady().then(() => {
  registerProtocol();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
