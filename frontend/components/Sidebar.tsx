"use client";

import { usePathname } from "next/navigation";
import Link from "next/link";
import { useState } from "react";
import {
  Home,
  User,
  BarChart2,
  BookOpen,
  LogOut,
  Menu,
  X,
  Activity,
  FileQuestion,
  Microscope,
  Library,
  History,
  Stethoscope,
  ClipboardList,
  PenTool,
  Users,
  LayoutDashboard,
  FileBox,
  Upload,
  Bell,
  Calendar,
  Brain,
  Sparkles,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import NotificationBell from "./NotificationBell";
import styles from "./Sidebar.module.css";

interface NavLink {
  href: string;
  icon: React.ReactNode;
  label: string;
}

export default function Sidebar() {
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const { user, logout } = useAuth();

  const commonLinks: NavLink[] = [
    { href: "/dashboard", icon: <Home size={20} />, label: "Home" },
    { href: "/profile", icon: <User size={20} />, label: "My Account" },
  ];

  const studentLinks: NavLink[] = [
    { href: "/statistics", icon: <BarChart2 size={20} />, label: "My Statistics" },
    { href: "/cases", icon: <BookOpen size={20} />, label: "Case Library" },
    { href: "/student/recommendations", icon: <Sparkles size={20} />, label: "Vaka Önerileri" },
    { href: "/oral-pathology", icon: <Microscope size={20} />, label: "Oral Pathology" },
    { href: "/quiz", icon: <FileQuestion size={20} />, label: "Klinik Bilgi Testi" },
    { href: "/student/question-bank", icon: <Library size={20} />, label: "Soru Bankası" },
    { href: "/student/history", icon: <History size={20} />, label: "Sınav Geçmişi" },
    { href: "/student/review-schedule", icon: <Brain size={20} />, label: "Tekrar Programı" },
    { href: "/student/mini-cases", icon: <Stethoscope size={20} />, label: "Mini Vakalar" },
    { href: "/student/notifications", icon: <Bell size={20} />, label: "Bildirimler" },
    { href: "/student/calendar", icon: <Calendar size={20} />, label: "Sınav Takvimi" },
  ];

  const instructorLinks: NavLink[] = [
    { href: "/instructor/dashboard", icon: <LayoutDashboard size={20} />, label: "Instructor Panel" },
    { href: "/instructor/questions", icon: <FileQuestion size={20} />, label: "Soru Yönetimi" },
    { href: "/instructor/grading", icon: <PenTool size={20} />, label: "Puanlama" },
    { href: "/instructor/mini-cases", icon: <Stethoscope size={20} />, label: "Mini Vakalar" },
    { href: "/instructor/mappings", icon: <ClipboardList size={20} />, label: "Eşlemeler" },
    { href: "/instructor/import", icon: <Upload size={20} />, label: "Soru İçe Aktar" },
    { href: "/instructor/question-stats", icon: <BarChart2 size={20} />, label: "Soru İstatistikleri" },
    { href: "/instructor/exam-schedules", icon: <Calendar size={20} />, label: "Sınav Takvimi" },
  ];

  const adminLinks: NavLink[] = [
    { href: "/admin/dashboard", icon: <LayoutDashboard size={20} />, label: "Admin Panel" },
    { href: "/admin/users", icon: <Users size={20} />, label: "Kullanıcılar" },
    { href: "/admin/cases", icon: <FileBox size={20} />, label: "Vakalar" },
  ];

  let navLinks: NavLink[] = [...commonLinks];
  const role = user?.role;

  if (role === "student") {
    navLinks = [...navLinks, ...studentLinks];
  } else if (role === "instructor") {
    navLinks = [...navLinks, ...studentLinks, ...instructorLinks];
  } else if (role === "admin") {
    navLinks = [...navLinks, ...studentLinks, ...instructorLinks, ...adminLinks];
  }

  const handleLogout = () => {
    logout();
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
          <NotificationBell />
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
            const isActive =
              pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsOpen(false)}
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
