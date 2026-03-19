# Sidebar Component Refactoring

## 📋 Overview

Refactored the DentAI project to use a **reusable sidebar component** instead of duplicating sidebar code across multiple pages.

---

## 🎯 Benefits

### ✅ **DRY Principle (Don't Repeat Yourself)**

- Single source of truth for sidebar logic
- No code duplication across pages
- Easier to maintain and update

### ✅ **Consistency**

- Uniform sidebar across all pages
- Standardized navigation experience
- Consistent styling and behavior

### ✅ **Flexibility**

- Configurable per page type
- Optional elements (case selector, model selector)
- Custom actions support

### ✅ **Maintainability**

- One place to update sidebar features
- Reduced bug surface area
- Easier testing

---

## 📁 New File Structure

```
app/
├── components/
│   ├── __init__.py         # Component exports
│   └── sidebar.py          # Reusable sidebar component
```

---

## 🔧 Component API

### **`render_sidebar()`**

```python
def render_sidebar(
    page_type: str = "default",
    show_case_selector: bool = True,
    show_model_selector: bool = False,
    custom_actions: Optional[Dict[str, Callable]] = None
) -> Dict[str, any]:
    """
    Render reusable sidebar with common elements.

    Args:
        page_type: Type of page ('chat', 'stats', 'home', 'default')
        show_case_selector: Whether to show case selection dropdown
        show_model_selector: Whether to show model selection dropdown
        custom_actions: Dictionary of {button_label: callback_function}

    Returns:
        Dictionary containing:
        - selected_case_id: Currently selected case ID
        - selected_case_name: Currently selected case name
        - selected_model: Currently selected model (if enabled)
    """
```

---

## 🔄 Migration Examples

### **Before (Old chat.py):**

```python
# 60+ lines of sidebar code
with st.sidebar:
    st.header("📂 Vaka Seçimi")
    show_profile_card()

    selected_case_name = st.selectbox(...)
    selected_case_id = CASE_OPTIONS[selected_case_name]

    if "current_case_id" not in st.session_state:
        st.session_state.current_case_id = selected_case_id

    if st.session_state.current_case_id != selected_case_id:
        st.session_state.current_case_id = selected_case_id
        st.session_state.messages = []
        st.session_state.db_session_id = None
        st.success(f"✅ Yeni vaka: {selected_case_name}")
        st.rerun()

    st.divider()
    st.header("🤖 Model Ayarları")
    # ... more code ...
```

### **After (New chat.py):**

```python
# Just 10 lines!
from app.components import render_sidebar

def reset_chat():
    st.session_state.messages = []
    st.session_state.db_session_id = None
    st.rerun()

sidebar_data = render_sidebar(
    page_type="chat",
    show_case_selector=True,
    show_model_selector=True,
    custom_actions={"🔄 Yeni Sohbet": reset_chat}
)
```

---

## 📄 Updated Files

### ✅ **Created:**

- `app/components/__init__.py` - Component exports
- `app/components/sidebar.py` - Reusable sidebar implementation

### ✅ **Refactored:**

- `pages/chat.py` - Now uses `render_sidebar()`
- `pages/stats.py` - Now uses `render_sidebar()`

### 📝 **To Refactor (Future):**

- `pages/home.py` - Can optionally use simplified sidebar
- `pages/medgemma.py` - Can integrate sidebar component

---

## 🎨 Sidebar Features

### **Included in All Pages:**

- ✅ Student profile card
- ✅ Navigation buttons (Home, Stats, Chat)
- ✅ System info (API status, active case, etc.)

### **Optional Per Page:**

- 🔘 Case selector dropdown
- 🔘 Model selector dropdown
- 🔘 Custom action buttons

### **Automatic Handling:**

- ✅ Case change detection & state reset
- ✅ Session state initialization
- ✅ Page-specific state management

---

## 🚀 Usage Examples

### **1. Chat Page (Full Features)**

```python
sidebar_data = render_sidebar(
    page_type="chat",
    show_case_selector=True,
    show_model_selector=True,
    custom_actions={
        "🔄 Yeni Sohbet": reset_chat,
        "📥 Kaydet": save_session
    }
)

# Access returned data
case_id = sidebar_data["selected_case_id"]
model = sidebar_data["selected_model"]
```

### **2. Stats Page (Minimal)**

```python
render_sidebar(
    page_type="stats",
    show_case_selector=False,
    show_model_selector=False
)
```

### **3. Custom Page (Selective)**

```python
def export_data():
    # Export logic
    pass

sidebar_data = render_sidebar(
    page_type="custom",
    show_case_selector=True,
    show_model_selector=False,
    custom_actions={
        "📤 Export": export_data
    }
)
```

---

## 📊 Code Reduction Stats

| Metric                     | Before | After | Improvement |
| -------------------------- | ------ | ----- | ----------- |
| **chat.py sidebar lines**  | ~65    | ~10   | **-85%**    |
| **stats.py sidebar lines** | ~50    | ~5    | **-90%**    |
| **Total duplicated lines** | ~115   | 0     | **-100%**   |
| **Maintainability**        | Low    | High  | **↑↑↑**     |

---

## 🔮 Future Enhancements

### **Potential Additions:**

1. **Sidebar Themes** - Light/dark mode toggle
2. **Collapsible Sections** - Expand/collapse sidebar sections
3. **User Preferences** - Remember user's sidebar state
4. **Analytics Widget** - Quick stats in sidebar
5. **Notification Center** - System messages/alerts

### **Configuration Extensions:**

```python
render_sidebar(
    page_type="chat",
    theme="dark",  # NEW
    collapsed_sections=["system_info"],  # NEW
    show_analytics=True,  # NEW
    notification_count=3  # NEW
)
```

---

## ✅ Testing Checklist

- [x] Sidebar renders correctly on chat page
- [x] Sidebar renders correctly on stats page
- [x] Case selector works and updates state
- [x] Model selector works (when enabled)
- [x] Custom actions execute callbacks
- [x] Navigation buttons switch pages correctly
- [x] Profile card displays properly
- [x] System info shows accurate data
- [x] Page-specific state resets on case change

---

## 📝 Developer Notes

### **Import Pattern:**

```python
from app.components import render_sidebar, CASE_OPTIONS, MODEL_OPTIONS
```

### **Common Pitfall:**

❌ **DON'T** call `render_sidebar()` inside a `with st.sidebar:` block
✅ **DO** call `render_sidebar()` directly - it handles the sidebar context internally

### **State Management:**

- Sidebar automatically initializes `current_case_id` in session state
- Page-specific state should be reset in custom action callbacks
- Use `sidebar_data` return value to access selected values

---

**Refactoring Date:** December 11, 2025  
**Pattern:** Component-Based Architecture  
**Status:** ✅ Production Ready
