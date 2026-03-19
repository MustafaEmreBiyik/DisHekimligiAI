"""
Analytics Engine - DentAI
Weakness Detection & Performance Analysis
"""

import pandas as pd
from typing import Dict, List, Any


def analyze_performance(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze student performance and identify weaknesses.
    
    Args:
        df: DataFrame with columns ['action', 'score', 'outcome']
    
    Returns:
        Dictionary with:
        - weakest_category: str (action type with lowest avg score)
        - weakest_score: float (average score of weakest category)
        - recommendation: str (Turkish recommendation text)
        - category_performance: dict (performance by category)
    """
    
    if df.empty or 'action' not in df.columns:
        return {
            "weakest_category": None,
            "weakest_score": 0,
            "recommendation": "Henüz yeterli veri yok. Daha fazla vaka çözmeye devam et!",
            "category_performance": {}
        }
    
    # Map action types to broader categories
    action_categories = {
        # Diagnosis actions
        'diagnose_lichen_planus': 'diagnosis',
        'diagnose_periodontitis': 'diagnosis',
        'diagnose_primary_herpes': 'diagnosis',
        'diagnose_behcet': 'diagnosis',
        'diagnose_secondary_syphilis': 'diagnosis',
        'diagnose_mucous_membrane_pemphigoid': 'diagnosis',
        
        # Anamnesis actions
        'take_anamnesis': 'anamnesis',
        'ask_symptom_onset': 'anamnesis',
        'ask_about_medications': 'anamnesis',
        'ask_systemic_symptoms': 'anamnesis',
        'ask_sexual_history': 'anamnesis',
        
        # Examination actions
        'perform_oral_exam': 'examination',
        'perform_nikolsky_test': 'examination',
        'examine_skin': 'examination',
        'examine_genitals': 'examination',
        
        # Lab/diagnostic tests
        'request_biopsy': 'diagnostic_tests',
        'request_blood_tests': 'diagnostic_tests',
        'request_serology': 'diagnostic_tests',
        'request_dif_biopsy': 'diagnostic_tests',
        'request_fungal_culture': 'diagnostic_tests',
        
        # Treatment actions
        'prescribe_topical_steroids': 'treatment',
        'prescribe_systemic_steroids': 'treatment',
        'prescribe_antibiotics': 'treatment',
        'prescribe_antivirals': 'treatment',
        'refer_to_specialist': 'treatment',
        'recommend_oral_hygiene': 'treatment'
    }
    
    # Add category column
    df['category'] = df['action'].map(action_categories).fillna('other')
    
    # Calculate performance by category
    category_stats = df.groupby('category').agg({
        'score': ['count', 'mean', 'sum']
    }).round(2)
    
    category_stats.columns = ['action_count', 'avg_score', 'total_score']
    
    # Filter categories with at least 2 actions for reliability
    significant_categories = category_stats[category_stats['action_count'] >= 2]
    
    if significant_categories.empty:
        # Not enough data in any category
        return {
            "weakest_category": None,
            "weakest_score": 0,
            "recommendation": "Henüz yeterli veri yok. Her kategoriden daha fazla eylem yapmaya çalış!",
            "category_performance": category_stats.to_dict('index')
        }
    
    # Find weakest category
    weakest = significant_categories['avg_score'].idxmin()
    weakest_score = significant_categories.loc[weakest, 'avg_score']
    
    # Generate recommendation based on weakest category
    recommendations = {
        'diagnosis': "⚠️ **Zayıf Alan: Tanı Koyma**\n\n"
                    "Tanılarında daha dikkatli ol. Öneri:\n"
                    "- Patoloji bulgularını detaylı incele\n"
                    "- Ayırıcı tanıları gözden geçir\n"
                    "- Klinik bulgularla laboratuvar sonuçlarını birleştir",
        
        'anamnesis': "⚠️ **Zayıf Alan: Anamnez Alma**\n\n"
                    "Hasta sorgulamasını geliştir. Öneri:\n"
                    "- Daha detaylı semptom sorgulaması yap\n"
                    "- Sistemik hastalık geçmişini mutlaka sor\n"
                    "- İlaç kullanımını ve alerjileri kontrol et",
        
        'examination': "⚠️ **Zayıf Alan: Klinik Muayene**\n\n"
                      "Muayene tekniklerini güçlendir. Öneri:\n"
                      "- Oral muayeneyi sistematik şekilde yap\n"
                      "- Özel testleri (Nikolsky, vb.) uygun zamanda kullan\n"
                      "- Ekstraoral bulguları da değerlendir",
        
        'diagnostic_tests': "⚠️ **Zayıf Alan: Tanısal Testler**\n\n"
                           "Test isteme stratejilerini iyileştir. Öneri:\n"
                           "- Hangi testlerin ne zaman gerekli olduğunu öğren\n"
                           "- Biyopsi endikasyonlarını gözden geçir\n"
                           "- Maliyet-etkinlik dengesini göz önünde bulundur",
        
        'treatment': "⚠️ **Zayıf Alan: Tedavi Planlaması**\n\n"
                    "Tedavi seçimlerini geliştir. Öneri:\n"
                    "- İlk basamak tedavileri önce dene\n"
                    "- Yan etkileri ve kontrendikasyonları kontrol et\n"
                    "- Hasta eğitimi ve takip planı yap"
    }
    
    recommendation = recommendations.get(weakest, "Genel performansını artırmaya devam et!")
    
    # Add score context
    if weakest_score < 5:
        strength_level = "🔴 Kritik"
    elif weakest_score < 7:
        strength_level = "🟡 Zayıf"
    else:
        strength_level = "🟢 İyileştirilebilir"
    
    recommendation = f"{strength_level} | Ortalama Puan: {weakest_score:.1f}/10\n\n{recommendation}"
    
    return {
        "weakest_category": weakest,
        "weakest_score": weakest_score,
        "recommendation": recommendation,
        "category_performance": category_stats.to_dict('index')
    }


def generate_report_text(stats: Dict[str, Any], analysis: Dict[str, Any]) -> str:
    """
    Generate downloadable text report of student performance.
    
    Args:
        stats: Statistics dictionary from database
        analysis: Analysis results from analyze_performance
    
    Returns:
        Formatted text report
    """
    
    action_history = stats.get('action_history', [])
    total_score = stats.get('total_score', 0)
    total_actions = stats.get('total_actions', 0)
    completed_cases = stats.get('completed_cases', set())
    
    avg_score = total_score / total_actions if total_actions > 0 else 0
    
    report = f"""
════════════════════════════════════════════════════════════
              DentAI - PERFORMANS KARNESI
════════════════════════════════════════════════════════════

📊 GENEL PERFORMANS
────────────────────────────────────────────────────────────
• Toplam Puan:           {total_score}
• Toplam Eylem:          {total_actions}
• Ortalama Puan/Eylem:   {avg_score:.2f}
• Tamamlanan Vaka:       {len(completed_cases)}

════════════════════════════════════════════════════════════

🎯 KATEGORI BAZLI PERFORMANS
────────────────────────────────────────────────────────────
"""
    
    # Add category performance
    if analysis.get('category_performance'):
        for category, perf in analysis['category_performance'].items():
            category_name_map = {
                'diagnosis': 'Tanı Koyma',
                'anamnesis': 'Anamnez Alma',
                'examination': 'Klinik Muayene',
                'diagnostic_tests': 'Tanısal Testler',
                'treatment': 'Tedavi',
                'other': 'Diğer'
            }
            
            cat_name = category_name_map.get(category, category)
            report += f"\n{cat_name}:\n"
            report += f"  - Eylem Sayısı:    {perf['action_count']:.0f}\n"
            report += f"  - Ortalama Puan:   {perf['avg_score']:.2f}\n"
            report += f"  - Toplam Puan:     {perf['total_score']:.0f}\n"
    
    report += "\n════════════════════════════════════════════════════════════\n\n"
    report += "💡 GELİŞİM ÖNERİSİ\n"
    report += "────────────────────────────────────────────────────────────\n"
    
    if analysis.get('recommendation'):
        # Remove markdown formatting for text file
        rec = analysis['recommendation'].replace('**', '').replace('⚠️', '!')
        report += rec
    
    report += "\n\n════════════════════════════════════════════════════════════\n"
    report += "📋 SON EYLEMLER (Son 10)\n"
    report += "────────────────────────────────────────────────────────────\n\n"
    
    if action_history:
        for i, action in enumerate(action_history[-10:], 1):
            report += f"{i}. {action.get('timestamp', 'N/A')}\n"
            report += f"   Vaka: {action.get('case_id', 'N/A')}\n"
            report += f"   Eylem: {action.get('action', 'N/A')}\n"
            report += f"   Puan: {action.get('score', 0)}\n"
            report += f"   Sonuç: {action.get('outcome', 'N/A')}\n\n"
    
    report += "════════════════════════════════════════════════════════════\n"
    report += "               DentAI ile başarılar!\n"
    report += "════════════════════════════════════════════════════════════\n"
    
    return report
