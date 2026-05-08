"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
<<<<<<< HEAD
import { useState } from "react";
=======
import { useState, useEffect } from "react";
>>>>>>> origin/main
import { Home, User, BarChart2, BookOpen, LogOut, Menu, X, Activity, FileQuestion } from "lucide-react";
import styles from "./Sidebar.module.css";

export default function Sidebar() {
  const pathname = usePathname();
<<<<<<< HEAD
  const [menuState, setMenuState] = useState({ pathname, isOpen: false });
  const isOpen = menuState.pathname === pathname ? menuState.isOpen : false;
  const openMenu = () => setMenuState({ pathname, isOpen: true });
  const closeMenu = () => setMenuState({ pathname, isOpen: false });
=======
  const [isOpen, setIsOpen] = useState(false);
>>>>>>> origin/main

  const navLinks = [
    { href: "/dashboard", icon: <Home size={20} />, label: "Home" },
    { href: "/profile", icon: <User size={20} />, label: "My Account" },
    { href: "/statistics", icon: <BarChart2 size={20} />, label: "My Statistics" },
    { href: "/cases", icon: <BookOpen size={20} />, label: "Case Library" },
    { href: "/quiz", icon: <FileQuestion size={20} />, label: "Klinik Bilgi Testi" },
  ];

<<<<<<< HEAD
=======
  // Close sidebar on route change for mobile
  useEffect(() => {
    setIsOpen(false);
  }, [pathname]);

>>>>>>> origin/main
  // Optionally add logout logic here
  const handleLogout = () => {
    console.log("Logout triggered");
  };

  return (
    <>
      <button 
        className={styles.mobileToggle} 
<<<<<<< HEAD
        onClick={openMenu}
=======
        onClick={() => setIsOpen(true)}
>>>>>>> origin/main
        aria-label="Open Menu"
      >
        <Menu size={24} />
      </button>

      <div 
        className={styles.overlay} 
        data-open={isOpen} 
<<<<<<< HEAD
        onClick={closeMenu} 
=======
        onClick={() => setIsOpen(false)} 
>>>>>>> origin/main
      />

      <aside className={styles.sidebarContainer} data-open={isOpen}>
        <div className={styles.logoArea}>
          <div className={styles.logoIcon}>
            <Activity size={28} />
          </div>
          <div className={styles.logoText}>DentAI</div>
          <button 
            className={styles.mobileClose} 
<<<<<<< HEAD
            onClick={closeMenu}
=======
            onClick={() => setIsOpen(false)}
>>>>>>> origin/main
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
<<<<<<< HEAD
                onClick={closeMenu}
=======
>>>>>>> origin/main
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
