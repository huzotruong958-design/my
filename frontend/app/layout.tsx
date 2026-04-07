import "./globals.css";

import { Sidebar } from "@/components/sidebar";

export const metadata = {
  title: "WeChat Travel Agents",
  description: "Admin console for multi-agent WeChat article automation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <div className="shell">
          <Sidebar />
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}

