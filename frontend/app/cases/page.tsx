"use client";

import React, { useState, useMemo } from "react";
import { Search, BookOpen, User, ChevronRight, Stethoscope } from "lucide-react";
import styles from "./Cases.module.css";
import { useRouter } from "next/navigation";

// --- TYPES & MOCK DATA ---
type Difficulty = "Kolay" | "Orta" | "Zor";

interface CaseScenario {
  id: string;
  title: string;
  difficulty: Difficulty;
  age: number;
  gender: string;
  description: string;
  tags: string[];
}

const mockCasesData: CaseScenario[] = [
  { 
    id: "olp_001", 
    title: "Oral Liken Planus", 
    difficulty: "Orta", 
    age: 45, 
    gender: "Kadın", 
    description: "Ağızda beyaz çizgiler ve yanma hissi", 
    tags: ["Anamnez", "Ayırıcı Tanı"] 
  },
  { 
    id: "perio_001", 
    title: "Kronik Periodontitis", 
    difficulty: "Zor", 
    age: 55, 
    gender: "Erkek", 
    description: "Dişetlerinde kanama ve diş sallantısı (Kalp pili!)", 
    tags: ["Risk Faktörü", "Sistemik Durum"] 
  },
  { 
    id: "herpes_primary_01", 
    title: "Primer Herpetik Gingivostomatitis", 
    difficulty: "Orta", 
    age: 6, 
    gender: "Çocuk", 
    description: "Ateş ve oral ülserler", 
    tags: ["Viral Enfeksiyon", "Vital Bulgular"] 
  },
  { 
    id: "behcet_01", 
    title: "Behçet Hastalığı", 
    difficulty: "Zor", 
    age: 32, 
    gender: "Erkek", 
    description: "Tekrarlayan oral ülserler", 
    tags: ["Paterji Testi", "Sistemik Hastalık"] 
  },
  { 
    id: "syphilis_02", 
    title: "Sekonder Sifiliz", 
    difficulty: "Zor", 
    age: 28, 
    gender: "Erkek", 
    description: "Ağızda beyaz lezyonlar", 
    tags: ["CYBH", "Seroloji"] 
  },
  { 
    id: "infectious_child_01", 
    title: "Primer Herpetik Gingivostomatitis (Pediatrik)", 
    difficulty: "Orta", 
    age: 4, 
    gender: "Çocuk", 
    description: "Yüksek ateş ve oral veziküller", 
    tags: ["Pediatri", "Viral Enfeksiyon"] 
  },
  { 
    id: "desquamative_01", 
    title: "Kronik Deskuamatif Gingivitis", 
    difficulty: "Zor", 
    age: 50, 
    gender: "Kadın", 
    description: "Dişetlerinde kızarıklık ve soyulma", 
    tags: ["Otoimmün", "Biyopsi"] 
  }
];

const FILTERS = ["Tümü", "Kolay", "Orta", "Zor"];

// --- MAIN COMPONENT ---
export default function CaseLibraryPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("Tümü");

  // Dynamic Filtering
  const filteredCases = useMemo(() => {
    return mockCasesData.filter((c) => {
      // 1. Difficulty Filter
      const matchesDifficulty = activeFilter === "Tümü" || c.difficulty === activeFilter;
      
      // 2. Text Search Filter (Matches Title or Description)
      const q = searchQuery.toLowerCase();
      const matchesSearch = c.title.toLowerCase().includes(q) || c.description.toLowerCase().includes(q);

      return matchesDifficulty && matchesSearch;
    });
  }, [searchQuery, activeFilter]);

  // Handle case start
  const handleStartCase = (id: string) => {
    router.push(`/chat/${id}`);
  };

  return (
    <div className={styles.container}>
      
      {/* HEADER */}
      <div className={styles.header}>
        <h1 className={styles.title}>
          <BookOpen size={36} color="#0066cc" />
          Vaka Kütüphanesi
        </h1>
        <p className={styles.subtitle}>Klinik becerilerinizi geliştirmek için bir hasta senaryosu seçin.</p>
      </div>

      {/* CONTROLS (Search & Filters) */}
      <div className={styles.controls}>
        <div className={styles.searchWrapper}>
          <Search size={22} className={styles.searchIcon} />
          <input 
            type="text" 
            className={styles.searchInput}
            placeholder="Vaka adı veya semptom ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className={styles.filters}>
          {FILTERS.map(filter => (
            <button
              key={filter}
              className={styles.filterBtn}
              data-active={activeFilter === filter}
              onClick={() => setActiveFilter(filter)}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* CASE GRID */}
      {filteredCases.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: '#a0aec0' }}>
          <Stethoscope size={64} style={{ opacity: 0.2, marginBottom: '1rem' }} />
          <h2>Eşleşen vaka bulunamadı.</h2>
          <p>Lütfen arama kriterlerinizi değiştirin.</p>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredCases.map(c => {
            
            // Assign Badge Color Class
            let badgeClass = styles.badgeKolay;
            if (c.difficulty === "Orta") badgeClass = styles.badgeOrta;
            if (c.difficulty === "Zor") badgeClass = styles.badgeZor;

            return (
              <div key={c.id} className={styles.caseCard}>
                
                <div className={styles.cardHeader}>
                  <h2 className={styles.caseTitle}>{c.title}</h2>
                  <div className={`${styles.badge} ${badgeClass}`}>
                    {c.difficulty}
                  </div>
                </div>

                <div className={styles.patientInfo}>
                  <User size={18} className={styles.patientInfoIcon} />
                  <span>{c.age} Yaşında • {c.gender}</span>
                </div>

                <p className={styles.desc}>{c.description}</p>

                <div className={styles.tags}>
                  {c.tags.map(tag => (
                    <span key={tag} className={styles.tag}>#{tag}</span>
                  ))}
                </div>

                <button 
                  className={styles.btnStart} 
                  onClick={() => handleStartCase(c.id)}
                >
                  <Stethoscope size={18} />
                  <span>Vakaya Başla</span>
                  <ChevronRight size={18} style={{ marginLeft: 'auto' }} />
                </button>
                
              </div>
            );
          })}
        </div>
      )}

    </div>
  );
}
