"""
BrainSAIT OCR Complete - Production-Ready Streamlit App
Best practice implementation with Tesseract OCR
100% Free deployment on Streamlit Community Cloud
"""

import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import pandas as pd
import io
import json
from datetime import datetime
import re
from pathlib import Path
import hashlib
import sqlite3
from typing import List, Dict, Optional
import base64

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="BrainSAIT OCR - برين سايت للتعرف الضوئي",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/Fadil369/brainsait-ocr',
        'Report a bug': 'https://github.com/Fadil369/brainsait-ocr/issues',
        'About': "# BrainSAIT OCR\nProfessional document processing with OCR"
    }
)

# Custom CSS for professional look
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin: 1rem 0;
    }
    .stat-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1E88E5;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 5px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .stDownloadButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Database initialization
@st.cache_resource
def init_database():
    """Initialize SQLite database for history tracking"""
    conn = sqlite3.connect('ocr_history.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ocr_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            file_hash TEXT UNIQUE,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size INTEGER,
            page_count INTEGER,
            language TEXT,
            character_count INTEGER,
            word_count INTEGER,
            processing_time REAL,
            success BOOLEAN DEFAULT 1
        )
    ''')
    
    conn.commit()
    return conn

# Initialize session state
if 'processing_history' not in st.session_state:
    st.session_state.processing_history = []

if 'current_results' not in st.session_state:
    st.session_state.current_results = None

class OCRProcessor:
    """Professional OCR processing engine"""
    
    def __init__(self):
        self.supported_formats = ['pdf', 'png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff']
    
    def calculate_file_hash(self, file_bytes: bytes) -> str:
        """Calculate SHA256 hash of file"""
        return hashlib.sha256(file_bytes).hexdigest()
    
    def extract_text_from_image(self, image: Image.Image, lang: str = 'eng+ara') -> str:
        """Extract text from image using Tesseract OCR"""
        try:
            # Enhance image quality for better OCR
            image = image.convert('L')  # Convert to grayscale
            text = pytesseract.image_to_string(image, lang=lang, config='--psm 3')
            return text
        except Exception as e:
            st.error(f"OCR Error: {str(e)}")
            return ""
    
    def extract_from_pdf(self, pdf_bytes: bytes, lang: str = 'eng+ara', 
                        use_ocr: bool = True, progress_callback=None) -> Dict:
        """Extract text from PDF with optional OCR"""
        results = {
            'pages': [],
            'total_text': '',
            'metadata': {},
            'tables': [],
            'page_count': 0
        }
        
        try:
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            results['page_count'] = pdf.page_count
            results['metadata'] = pdf.metadata
            
            for page_num in range(pdf.page_count):
                if progress_callback:
                    progress_callback(page_num + 1, pdf.page_count)
                
                page = pdf[page_num]
                
                # Try standard text extraction first
                text = page.get_text()
                
                # Use OCR if text is minimal and OCR is enabled
                if use_ocr and len(text.strip()) < 50:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text = self.extract_text_from_image(img, lang)
                
                # Detect tables
                tables = self.detect_tables(text)
                
                page_data = {
                    'page_number': page_num + 1,
                    'text': text,
                    'char_count': len(text),
                    'word_count': len(text.split()),
                    'tables': tables
                }
                
                results['pages'].append(page_data)
                results['total_text'] += f"\n\n=== Page {page_num + 1} ===\n\n{text}"
                results['tables'].extend(tables)
            
            pdf.close()
            
        except Exception as e:
            st.error(f"PDF Processing Error: {str(e)}")
        
        return results
    
    def detect_tables(self, text: str) -> List[Dict]:
        """Detect table structures in text"""
        tables = []
        lines = text.split('\n')
        
        current_table = []
        in_table = False
        
        for line in lines:
            # Detect table rows (2+ columns separated by whitespace or tabs)
            parts = re.split(r'\s{2,}|\t', line.strip())
            
            if len(parts) >= 2:
                if not in_table:
                    in_table = True
                    current_table = []
                current_table.append(parts)
            else:
                if in_table and len(current_table) >= 2:
                    tables.append({
                        'rows': len(current_table),
                        'columns': max(len(row) for row in current_table),
                        'data': current_table
                    })
                in_table = False
                current_table = []
        
        # Add last table if exists
        if in_table and len(current_table) >= 2:
            tables.append({
                'rows': len(current_table),
                'columns': max(len(row) for row in current_table),
                'data': current_table
            })
        
        return tables
    
    def extract_from_image(self, image_bytes: bytes, lang: str = 'eng+ara') -> Dict:
        """Extract text from image"""
        results = {
            'text': '',
            'char_count': 0,
            'word_count': 0,
            'tables': []
        }
        
        try:
            img = Image.open(io.BytesIO(image_bytes))
            text = self.extract_text_from_image(img, lang)
            tables = self.detect_tables(text)
            
            results['text'] = text
            results['char_count'] = len(text)
            results['word_count'] = len(text.split())
            results['tables'] = tables
            
        except Exception as e:
            st.error(f"Image Processing Error: {str(e)}")
        
        return results

def get_download_link(data: str, filename: str, mime_type: str) -> str:
    """Generate download link for data"""
    b64 = base64.b64encode(data.encode()).decode()
    return f'<a href="data:{mime_type};base64,{b64}" download="{filename}">Download {filename}</a>'

def main():
    # Header
    st.markdown('<h1 class="main-header">🔍 BrainSAIT OCR</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">برين سايت للتعرف الضوئي على النصوص - Professional Document Processing</p>', 
                unsafe_allow_html=True)
    
    # Initialize database
    db_conn = init_database()
    
    # Initialize OCR processor
    processor = OCRProcessor()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Settings / الإعدادات")
        
        # Language selection
        languages = {
            'English + Arabic / العربية + الإنجليزية': 'eng+ara',
            'English only / الإنجليزية فقط': 'eng',
            'Arabic only / العربية فقط': 'ara',
            'French + Arabic / الفرنسية + العربية': 'fra+ara',
            'Spanish + English / الإسبانية + الإنجليزية': 'spa+eng',
        }
        
        selected_lang = st.selectbox(
            "OCR Language / لغة التعرف",
            options=list(languages.keys()),
            index=0
        )
        lang_code = languages[selected_lang]
        
        # OCR options
        enable_ocr = st.checkbox("Enable OCR for scanned PDFs / تفعيل التعرف الضوئي", value=True)
        extract_tables = st.checkbox("Extract Tables / استخراج الجداول", value=True)
        
        # Export format
        export_format = st.radio(
            "Export Format / صيغة التصدير",
            options=['Text (.txt)', 'CSV (.csv)', 'JSON (.json)', 'Markdown (.md)'],
            index=0
        )
        
        st.divider()
        
        # Statistics
        st.header("📊 Statistics / الإحصائيات")
        cursor = db_conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(character_count) FROM ocr_results WHERE success = 1")
        total_files, total_chars = cursor.fetchone()
        
        st.metric("Total Files Processed / الملفات المعالجة", total_files or 0)
        st.metric("Total Characters / إجمالي الأحرف", f"{total_chars or 0:,}")
    
    # Main content
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📤 Upload Document / رفع المستند")
        
        uploaded_file = st.file_uploader(
            "Choose PDF or Image file / اختر ملف PDF أو صورة",
            type=processor.supported_formats,
            help="Supported formats: PDF, PNG, JPG, JPEG, WEBP, BMP, TIFF"
        )
    
    with col2:
        if uploaded_file is not None:
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            st.info(f"📦 Size: {uploaded_file.size / 1024:.2f} KB")
            
            file_ext = uploaded_file.name.split('.')[-1].lower()
            st.info(f"📄 Type: {file_ext.upper()}")
    
    # Processing
    if uploaded_file is not None:
        if st.button("🚀 Start Processing / بدء المعالجة", type="primary", use_container_width=True):
            
            # Read file
            file_bytes = uploaded_file.read()
            file_hash = processor.calculate_file_hash(file_bytes)
            file_ext = uploaded_file.name.split('.')[-1].lower()
            
            # Check if already processed (cache)
            cursor = db_conn.cursor()
            cursor.execute("SELECT * FROM ocr_results WHERE file_hash = ?", (file_hash,))
            cached_result = cursor.fetchone()
            
            if cached_result:
                st.info("💾 This file was processed before. Using cached results.")
            
            # Process file
            start_time = datetime.now()
            
            with st.spinner('⏳ Processing... Please wait / جارٍ المعالجة... يرجى الانتظار'):
                # Progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current, total):
                    progress = current / total
                    progress_bar.progress(progress)
                    status_text.text(f"Processing page {current}/{total}...")
                
                # Process based on file type
                if file_ext == 'pdf':
                    results = processor.extract_from_pdf(
                        file_bytes, 
                        lang=lang_code, 
                        use_ocr=enable_ocr,
                        progress_callback=update_progress
                    )
                else:
                    results = processor.extract_from_image(file_bytes, lang=lang_code)
                    results['pages'] = [{'page_number': 1, 'text': results['text'], 
                                        'char_count': results['char_count'],
                                        'word_count': results['word_count']}]
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                progress_bar.empty()
                status_text.empty()
            
            # Store results
            st.session_state.current_results = results
            
            # Save to database
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO ocr_results 
                    (filename, file_hash, file_size, page_count, language, 
                     character_count, word_count, processing_time, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    uploaded_file.name,
                    file_hash,
                    uploaded_file.size,
                    len(results.get('pages', [])),
                    lang_code,
                    len(results.get('total_text', results.get('text', ''))),
                    sum(p['word_count'] for p in results.get('pages', [])),
                    processing_time,
                    1
                ))
                db_conn.commit()
            except Exception as e:
                st.warning(f"Could not save to history: {str(e)}")
            
            st.success(f"✅ Processing complete in {processing_time:.2f} seconds!")
            
            # Display results
            st.header("📊 Results / النتائج")
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Pages / الصفحات", len(results.get('pages', [])))
            
            with col2:
                total_chars = len(results.get('total_text', results.get('text', '')))
                st.metric("Characters / الأحرف", f"{total_chars:,}")
            
            with col3:
                total_words = sum(p['word_count'] for p in results.get('pages', []))
                st.metric("Words / الكلمات", f"{total_words:,}")
            
            with col4:
                tables_count = len(results.get('tables', []))
                st.metric("Tables / الجداول", tables_count)
            
            # Tabs for different views
            tab1, tab2, tab3, tab4 = st.tabs([
                "📝 Text / النص", 
                "📊 Tables / الجداول", 
                "🔍 Search / البحث",
                "💾 Export / التصدير"
            ])
            
            with tab1:
                if file_ext == 'pdf' and len(results.get('pages', [])) > 1:
                    page_num = st.selectbox(
                        "Select Page / اختر الصفحة",
                        options=range(1, len(results['pages']) + 1),
                        format_func=lambda x: f"Page {x} / صفحة {x}"
                    )
                    
                    page_data = results['pages'][page_num - 1]
                    st.text_area(
                        f"Text from Page {page_num} / النص من الصفحة {page_num}",
                        value=page_data['text'],
                        height=400
                    )
                else:
                    st.text_area(
                        "Extracted Text / النص المستخرج",
                        value=results.get('text', results.get('total_text', '')),
                        height=400
                    )
            
            with tab2:
                if results.get('tables'):
                    st.subheader(f"Found {len(results['tables'])} tables / تم العثور على {len(results['tables'])} جدول")
                    
                    for idx, table in enumerate(results['tables'], 1):
                        st.markdown(f"**Table {idx}** - {table['rows']} rows × {table['columns']} columns")
                        
                        # Convert to DataFrame
                        try:
                            df = pd.DataFrame(table['data'])
                            st.dataframe(df, use_container_width=True)
                            
                            # Download table as CSV
                            csv = df.to_csv(index=False)
                            st.download_button(
                                label=f"📥 Download Table {idx} CSV",
                                data=csv,
                                file_name=f"table_{idx}_{uploaded_file.name}.csv",
                                mime="text/csv"
                            )
                        except Exception as e:
                            st.error(f"Could not format table: {str(e)}")
                        
                        st.divider()
                else:
                    st.info("No tables detected / لم يتم العثور على جداول")
            
            with tab3:
                search_term = st.text_input("🔍 Search in document / البحث في المستند")
                
                if search_term:
                    full_text = results.get('total_text', results.get('text', ''))
                    matches = []
                    
                    for page in results.get('pages', []):
                        lines = page['text'].split('\n')
                        for line_num, line in enumerate(lines):
                            if search_term.lower() in line.lower():
                                matches.append({
                                    'Page': page['page_number'],
                                    'Line': line.strip(),
                                    'Preview': line[:100] + '...' if len(line) > 100 else line
                                })
                    
                    if matches:
                        st.success(f"✅ Found {len(matches)} matches / تم العثور على {len(matches)} تطابق")
                        df_matches = pd.DataFrame(matches)
                        st.dataframe(df_matches, use_container_width=True)
                    else:
                        st.warning(f"No matches found for '{search_term}' / لا توجد نتائج")
            
            with tab4:
                st.subheader("💾 Export Options / خيارات التصدير")
                
                full_text = results.get('total_text', results.get('text', ''))
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Text export
                    st.download_button(
                        label="📄 Download as TXT / تحميل كنص",
                        data=full_text,
                        file_name=f"{uploaded_file.name}_extracted.txt",
                        mime="text/plain",
                        use_container_width=True
                    )
                    
                    # Markdown export
                    markdown_text = f"# {uploaded_file.name}\n\n{full_text}"
                    st.download_button(
                        label="📝 Download as Markdown / تحميل كـ Markdown",
                        data=markdown_text,
                        file_name=f"{uploaded_file.name}_extracted.md",
                        mime="text/markdown",
                        use_container_width=True
                    )
                
                with col2:
                    # JSON export
                    json_data = json.dumps(results, indent=2, ensure_ascii=False)
                    st.download_button(
                        label="📊 Download as JSON / تحميل كـ JSON",
                        data=json_data,
                        file_name=f"{uploaded_file.name}_analysis.json",
                        mime="application/json",
                        use_container_width=True
                    )
                    
                    # CSV export (pages summary)
                    if results.get('pages'):
                        df_pages = pd.DataFrame([
                            {
                                'Page': p['page_number'],
                                'Characters': p['char_count'],
                                'Words': p['word_count']
                            }
                            for p in results['pages']
                        ])
                        csv = df_pages.to_csv(index=False)
                        st.download_button(
                            label="📈 Download Summary CSV / تحميل ملخص CSV",
                            data=csv,
                            file_name=f"{uploaded_file.name}_summary.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
    
    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p><strong>BrainSAIT OCR</strong> - Professional Document Processing</p>
        <p>Powered by Tesseract OCR | Built with Streamlit</p>
        <p>© 2026 Dr. Mohammed Al-Fadil | BrainSAIT</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
