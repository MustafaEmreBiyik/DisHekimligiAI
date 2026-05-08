"use client";

import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar";
import styles from "./AppLayout.module.css";
import React from "react";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Hide sidebar on auth pages
  const noSidebarRoutes = ["/", "/login", "/register"];
  const hasSidebar = !noSidebarRoutes.includes(pathname);

  return (
    <div className={styles.appWrapper}>
      {hasSidebar && <Sidebar />}
      <main className={styles.mainContent} data-has-sidebar={hasSidebar}>
        {children}
      </main>
    </div>
  );
}
