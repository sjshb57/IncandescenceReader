const { app, BrowserWindow, protocol } = require('electron');
const path = require('path');
const fs   = require('fs');

// ── 数据目录：打包后在 resources/wayback_snapshots，开发时在项目根目录
function getDataRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'wayback_snapshots');
  }
  return path.join(__dirname, 'wayback_snapshots');
}

// ── 注册自定义协议 incr://，让 Reader.html 通过它读取本地文件
// 这样完全绕开 file:// 的跨域限制，fetch() 正常工作
function registerProtocol() {
  protocol.registerFileProtocol('incr', (request, callback) => {
    // incr://local/wayback_snapshots/index.json
    // incr://local/Reader.html
    let urlPath = request.url.replace('incr://local/', '');
    // 解码 URI
    urlPath = decodeURIComponent(urlPath);

    let filePath;
    if (urlPath.startsWith('wayback_snapshots/')) {
      filePath = path.join(getDataRoot(), urlPath.replace('wayback_snapshots/', ''));
    } else {
      filePath = path.join(__dirname, urlPath);
    }

    callback({ path: filePath });
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

  // 开发模式直接加载文件，打包后用自定义协议
  if (app.isPackaged) {
    win.loadURL('incr://local/Reader.html');
  } else {
    // 开发时直接用 file:// 也可以，但 fetch 会失败
    // 用自定义协议统一
    win.loadURL('incr://local/Reader.html');
  }

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
