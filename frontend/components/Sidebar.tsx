"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useState, useEffect } from "react";
import { Home, User, BarChart2, BookOpen, Sparkles, LogOut, Menu, X, Activity } from "lucide-react";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);

  const navLinks = [
    { href: "/dashboard", icon: <Home size={20} />, label: "Home" },
    { href: "/profile", icon: <User size={20} />, label: "My Account" },
    { href: "/statistics", icon: <BarChart2 size={20} />, label: "My Statistics" },
    { href: "/cases", icon: <BookOpen size={20} />, label: "Case Library" },
    { href: "/medgemma", icon: <Sparkles size={20} />, label: "MedGemma" },
  ];

  // Close sidebar on route change for mobile
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

  // Optionally add logout logic here
  const handleLogout = () => {
    console.log("Logout triggered");
  };

  return (
    <>
      <button 
        className={styles.mobileToggle} 
        onClick={() => setIsOpen(true)}
        aria-label="Open Menu"
      >
        <Menu size={24} />
      </button>

      <div 
        className={styles.overlay} 
        data-open={isOpen} 
        onClick={() => setIsOpen(false)} 
      />

      <aside className={styles.sidebarContainer} data-open={isOpen}>
        <div className={styles.logoArea}>
          <div className={styles.logoIcon}>
            <Activity size={28} />
          </div>
          <div className={styles.logoText}>DentAI</div>
          <button 
            className={styles.mobileClose} 
            onClick={() => setIsOpen(false)}
            aria-label="Close Menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className={styles.navMenu}>
          {navLinks.map((link) => {
            const isActive = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link 
                key={link.href} 
                href={link.href}
                className={styles.navItem}
                data-active={isActive}
              >
                {link.icon}
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className={styles.footer}>
          <button className={styles.logoutBtn} onClick={handleLogout}>
            <LogOut size={20} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}
