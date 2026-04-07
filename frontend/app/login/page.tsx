export default function LoginPage() {
  return (
    <div className="stack">
      <div className="hero">
        <div className="eyebrow">Auth</div>
        <h1 style={{ margin: 0 }}>系统账号登录</h1>
        <p className="muted">后台登录和公众号授权绑定是两条独立流程。</p>
      </div>
      <form className="panel stack" style={{ maxWidth: 460 }}>
        <label>
          邮箱
          <input placeholder="operator@example.com" />
        </label>
        <label>
          密码
          <input type="password" placeholder="********" />
        </label>
        <button type="button">登录</button>
      </form>
    </div>
  );
}

