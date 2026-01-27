import re
import fitz  # PyMuPDF
import pandas as pd
import numpy as np

from fuzzywuzzy import fuzz

class PDFReader:
    def __init__(self, MIN_WORDS_PER_PARAGRAPH = 6, ##20
                       MAX_PARAGRAPH_REPETITIONS = 3,
                       LINE_GAP = 10,
                       TAP_GAP = 5,
                       FONT_PATH=None):
        self.ALLOWED_EXTENSIONS = {"pdf"}
        
        self.MIN_WORDS_PER_PARAGRAPH = MIN_WORDS_PER_PARAGRAPH
        self.LINE_GAP = LINE_GAP
        self.TAP_GAP = TAP_GAP
        self.MAX_PARAGRAPH_REPETITIONS = MAX_PARAGRAPH_REPETITIONS
        
        if FONT_PATH is not None:
            self.font_path = f"{FONT_PATH}TimesNewRomanPSMT Regular.ttf"
            self.custom_font = fitz.Font(fontfile=self.font_path)
        
    
    def PDF_to_dataframe(self, pdf_path):
        pdf_df = self.read_pdf(pdf_path)
        df_lines = self.set_lines(pdf_df)
        df_lines = self.filter_lines(df_lines)
        df_paragraphs = self.set_paragraphs_intelligent(df_lines)
        df_paragraphs = self.filter_paragraphs(df_paragraphs)
        return df_paragraphs, df_lines
        
    ############################################
    ###             Read PDF                 ###
    ############################################
    
    def get_text_bbox(self, full_text, evidence_snippet, df_lines, page_num):
        if not evidence_snippet or len(evidence_snippet.strip()) < 3:
            return None

        page_lines = df_lines[df_lines['page'] == page_num].copy()
        if page_lines.empty:
            return None

        snippet_clean = re.sub(r'\s+', ' ', evidence_snippet.strip().lower())
        
        matching_boxes = []
        for _, line in page_lines.iterrows():
            line_text = str(line['text']).strip().lower()
            if not line_text: continue

            if line_text in snippet_clean or snippet_clean in line_text or fuzz.partial_ratio(line_text, snippet_clean) > 90:
                matching_boxes.append([line['x0'], line['y0'], line['x1'], line['y1']])

        if not matching_boxes:
            return None

        x0 = min(box[0] for box in matching_boxes)
        y0 = min(box[1] for box in matching_boxes)
        x1 = max(box[2] for box in matching_boxes)
        y1 = max(box[3] for box in matching_boxes)

        return [x0, y0, x1, y1]

    def _allowed_file(self, filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def _is_watermark(self, span):
        return span.get("opacity", 1) < 1 or span["size"] > 20

    def _int_to_rgb(self, color_int):
        r = (color_int >> 16) & 255
        g = (color_int >> 8) & 255
        b = color_int & 255
        return (r / 255.0, g / 255.0, b / 255.0)

    def read_pdf(self, pdf_path, rewrite_pdf=False):
        # open the input file
        doc = fitz.open(pdf_path)
        
        if rewrite_pdf:
            # This will hold the cleaned pages
            new_doc = fitz.open()
            pdf_name = pdf_path.replace(".pdf", "")
        
        all_lines = []
        
        for page_num, page in enumerate(doc):
            blocks = page.get_text("dict")["blocks"]
        
            if rewrite_pdf:
                new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
    
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = "".join([span["text"].strip() for span in line["spans"]])
                        
                        for span in line["spans"]:
                            if self._is_watermark(span):
                                continue  # Skip watermark spans
        
                            # Get span properties
                            text = span["text"].strip()
                            x0, y0, x1, y1 = span["bbox"]
                            position = fitz.Point(span["bbox"][0], span["bbox"][1])
                            font_size = span["size"]
                            font = span["font"]
                            color = self._int_to_rgb(span["color"])
                            
                            all_lines.append([
                                page_num+1, font, text, y0, x0, y1, x1, 
                                color, len(text.split()), font_size
                            ])
        
                            # Re-insert text in the new page
                            if rewrite_pdf:
                                new_page.insert_text(
                                    position,
                                    text,
                                    fontfile=self.font_path if hasattr(self, 'font_path') else None,
                                    fontsize=font_size,
                                    color=color,
                                    overlay=True
                                )
    
        if rewrite_pdf:
            new_doc.save(f"{pdf_name}_wo_watermaks.pdf")
            new_doc.close()
        doc.close()
    
        columns = ["page", "font", "text", "y0", "x0", "y1", "x1", "color", "tokens", "font_size"]
        df = pd.DataFrame(all_lines, columns=columns)
        df.sort_values(by=["page", "y0", "x0"], inplace=True)
        
        # Calcular altura de cada span
        df['height'] = df['y1'] - df['y0']
        
        for page_num in df["page"].unique():
            __ = df[df["page"]==page_num].shape[0]
            df.loc[df["page"]==page_num, "paragraph_enum"] = range(1, __+1)
            
        df["paragraph_enum"] = df["paragraph_enum"].astype(int)
        
        df = df[["page", "paragraph_enum", "font", "text", "y0", "x0", "y1", "x1", 
                 "color", "tokens", "font_size", "height"]].copy()
        df_res = df.loc[df['tokens'] != 0]
        df_res = df_res.loc[df['text'] != ',']
        df_res = df_res.loc[df['text'] != '"']
        df_res = df_res.loc[df['text'] != '.']
        df_res = df_res.loc[df['text'] != 'o']
        df_res = df_res.reset_index(drop=True)
        return df_res
        
        
    ###########################################
    ###             Set Lines               ###
    ###########################################

    def _process_boxes(self, bboxes):
        # join squares
        x_min = min(box[0] for box in bboxes)
        y_min = min(box[1] for box in bboxes)
        x_max = max(box[2] for box in bboxes)
        y_max = max(box[3] for box in bboxes)

        return x_min, y_min, x_max, y_max

    def filter_lines(self, _df):
        df = _df.copy()
        similar_texts = []
        repeatd_ids = []

        df["empty_line"] = False
        df["only_special"] = df.text.apply( lambda x: re.sub(r"[^a-zA-Z0-9\s]", "", x).strip() )
        df["only_special_len"] = df.only_special.apply( lambda x: len(x.split()))

        df['text_wo_numbers'] = df.text.str.replace('\d*', '', regex=True)
        df['text_wo_numbers_len'] = df.text_wo_numbers.apply(lambda x: len(x.split()))
    
        df['text_duplicated'] = df.text_wo_numbers.duplicated(keep=False)
    
        for index, row in df.iterrows():
            num_paragraph = index+1
            if row["only_special_len"] == 0:
                df.loc[index, "empty_line"] = True

        df['to_delete_line'] = df.empty_line | df.text_duplicated
        
        df_deleted = df[~df.to_delete_line].copy()
        return df_deleted


    def set_lines(self, _df, y_tolerance=2.5):
        df = _df.copy()
        df.sort_values(by=["page", "y0", "x0"], inplace=True)
        doc_df = pd.DataFrame()

        for cur_page in sorted(df["page"].unique()):
            page_df = df[df["page"] == cur_page]

            lines_txt = []
            cur_line_words = []
            cur_line_boxes = []
            cur_line_y = None
            line_enum = 0

            for _, row in page_df.iterrows():
                x0, y0, x1, y1 = row["x0"], row["y0"], row["x1"], row["y1"]

                # Start new line if first word OR y0 differs too much from current line
                if cur_line_y is None or abs(y0 - cur_line_y) > y_tolerance:
                    if cur_line_words:  # save previous line
                        line_raw = " ".join(cur_line_words)
                        tokens = len(line_raw.split())
                        x_min, y_min, x_max, y_max = self._process_boxes(cur_line_boxes)
                        lines_txt.append([cur_page, line_enum, line_raw, tokens, x_min, y_min, x_max, y_max])
                        line_enum += 1

                    # reset for new line
                    cur_line_words = []
                    cur_line_boxes = []
                    cur_line_y = y0

                # collect this word
                if row["tokens"] > 0:
                    cur_line_words.append(row["text"])
                    cur_line_boxes.append([x0, y0, x1, y1])

            # save last line on page
            if cur_line_words:
                line_raw = " ".join(cur_line_words)
                tokens = len(line_raw.split())
                x_min, y_min, x_max, y_max = self._process_boxes(cur_line_boxes)
                lines_txt.append([cur_page, line_enum, line_raw, tokens, x_min, y_min, x_max, y_max])

            page_out = pd.DataFrame(
                lines_txt,
                columns=["page", "line_enum", "text", "tokens", "x0", "y0", "x1", "y1"]
            )
            doc_df = pd.concat([doc_df, page_out], ignore_index=True)

        # width & height
        doc_df["width"] = round(doc_df.x1 - doc_df.x0 + 0.025, 5)
        doc_df["height"] = round(doc_df.y1 - doc_df.y0 + 0.025, 5)

        # clean spaces in the *line-level* text
        doc_df["text"] = doc_df["text"].apply(lambda x: re.sub(r"\s+", " ", x).strip())

        return doc_df
        
        
    ############################################
    ###             Paragraph                ###
    ############################################
    
    def _analyze_page_statistics(self, page_df):
        if page_df.empty:
            return {}
        
        # Estadísticas de altura de líneas
        heights = page_df['height'].values
        font_sizes = page_df['font_size'].values if 'font_size' in page_df.columns else []
        
        # Calcular gaps entre líneas consecutivas
        page_df_sorted = page_df.sort_values(by=["y0", "x0"])
        gaps = []
        for i in range(1, len(page_df_sorted)):
            current_y = page_df_sorted.iloc[i]['y0']
            prev_y = page_df_sorted.iloc[i-1]['y1']
            gap = current_y - prev_y
            if gap > 0:  # Solo gaps positivos
                gaps.append(gap)
        
        stats_dict = {
            'mean_height': np.mean(heights) if len(heights) > 0 else 12,
            'median_height': np.median(heights) if len(heights) > 0 else 12,
            'std_height': np.std(heights) if len(heights) > 0 else 2,
            'mean_font_size': np.mean(font_sizes) if len(font_sizes) > 0 else 12,
            'gaps': gaps,
            'mean_gap': np.mean(gaps) if len(gaps) > 0 else 2,
            'median_gap': np.median(gaps) if len(gaps) > 0 else 2,
            'std_gap': np.std(gaps) if len(gaps) > 0 else 1,
        }
        
        # Identificar gaps típicos de línea vs párrafo usando clustering simple
        if len(gaps) > 3:
            gaps_array = np.array(gaps)
            # Separar en dos grupos: gaps pequeños (líneas) y gaps grandes (párrafos)
            q75 = np.percentile(gaps_array, 75)
            q25 = np.percentile(gaps_array, 25)
            
            # Gap típico entre líneas del mismo párrafo
            line_gaps = gaps_array[gaps_array <= q75]
            stats_dict['typical_line_gap'] = np.mean(line_gaps) if len(line_gaps) > 0 else stats_dict['mean_gap']
            
            # Threshold dinámico para párrafos - AJUSTADO PARA SER MÁS SENSIBLE
            stats_dict['dynamic_paragraph_threshold'] = max(
                stats_dict['typical_line_gap'] * 1.2,  # Reducido de 1.5 a 1.2
                stats_dict['mean_height'] * 0.6,       # Reducido de 0.8 a 0.6
                q25 + (stats_dict['std_gap'] * 0.3)    # Más sensible
            )
        else:
            stats_dict['typical_line_gap'] = stats_dict['mean_gap']
            stats_dict['dynamic_paragraph_threshold'] = max(
                stats_dict['mean_height'] * 0.6,       # Más sensible
                stats_dict['mean_gap'] * 1.2           # Más sensible
            )
        
        return stats_dict

    def _is_paragraph_break(self, current_row, prev_row, stats, prev_text=""):
        """
        Versión mejorada para documentos jurídicos con detección de párrafos,
        incluyendo indentación horizontal y manejo de bloques en MAYÚSCULAS.
        """
        import re

        if prev_row is None:
            return False

        # Vertical and horizontal distances
        vertical_gap = current_row['y0'] - prev_row['y1']
        horizontal_shift = current_row['x0'] - prev_row['x0']  # signed!

        curr_text = current_row.get('text', '').strip()
        prev_text_clean = prev_text.strip()

        gap_threshold = stats.get('dynamic_paragraph_threshold', 8)
        typical_gap = stats.get('typical_line_gap', 2)
        mean_height = stats.get('mean_height', 12)

        # === Helper: check ALL CAPS line ===
        def is_all_caps(text, min_len=5):
            letters = [c for c in text if c.isalpha()]
            if not letters or len(text) < min_len:
                return False
            upper_ratio = sum(c.isupper() for c in letters) / len(letters)
            return upper_ratio > 0.8

        curr_is_all_caps = is_all_caps(curr_text)
        prev_is_all_caps = is_all_caps(prev_text_clean)
        caps_to_normal = prev_is_all_caps and not curr_is_all_caps

        # === Criteria ===
        significant_vertical_gap = vertical_gap > gap_threshold
        indent_threshold = mean_height * 0.3

        # Indentation criteria
        significant_indent_right = horizontal_shift > indent_threshold
        significant_indent_left = horizontal_shift < -indent_threshold

        prev_ends_sentence = bool(
            prev_text_clean
            and (
                prev_text_clean.endswith(('.', '!', '?', ':', ';'))
                or prev_text_clean.endswith('."')
                or prev_text_clean.endswith('.)')
                or prev_text_clean.endswith('".')
                or prev_text_clean.endswith('").')
                or prev_text_clean.endswith('"),')
                or prev_text_clean.endswith('";')
                or prev_text_clean.endswith('":')
            )
        )

        starts_like_paragraph = bool(curr_text and (
            curr_text[0].isupper()
            or re.match(r'^[IVX]+\.', curr_text)
            or re.match(r'^\d+\.', curr_text)
            or re.match(r'^[a-z]\)', curr_text)
            or curr_text.startswith(('•', '-', '*', '(', '['))
            or curr_text.lower().startswith((
                'art.', 'artigo', 'parágrafo', '§', 'inciso',
                'considerando', 'portanto', 'assim', 'desta',
                'neste', 'pelo', 'conforme', 'segundo',
                'outrossim', 'ademais', 'contudo', 'todavia',
                'entretanto', 'por', 'ante', 'diante', 'face'
            ))
        ))

        prev_is_short = len(prev_text_clean.split()) < 8
        much_larger_gap = vertical_gap > (typical_gap * 1.5)
        prev_is_title = bool(prev_text_clean and (
            prev_text_clean.isupper() and len(prev_text_clean) > 5
            or prev_text_clean.endswith(':') and len(prev_text_clean.split()) < 10
        ))

        is_continuation = bool(curr_text and (
            curr_text[0].islower()
            or curr_text.startswith(('e ', 'ou ', 'de ', 'da ', 'do ', 'na ', 'no ', 'para ', 'com ', 'em '))
            or prev_text_clean.endswith((',', ' e', ' ou', ' de', ' da', ' do'))
        ))

        # === Decision logic (priority: vertical gap first) ===
        is_break = False

        # 1. Strong vertical gap signals
        if significant_vertical_gap:
            is_break = True
        elif much_larger_gap and (prev_ends_sentence or starts_like_paragraph):
            is_break = True

        # 2. All-caps / title formatting signals
        elif prev_is_all_caps and curr_is_all_caps:
            # Keep consecutive ALL CAPS lines together
            is_break = False
        elif caps_to_normal:
            # Break when ALL CAPS block ends and paragraph begins
            is_break = True
        elif prev_is_title and vertical_gap > typical_gap * 0.8:
            is_break = True

        # 3. Sentence structure signals
        elif prev_ends_sentence and starts_like_paragraph and vertical_gap > typical_gap:
            is_break = True

        # 4. Weaker heuristics
        #elif (significant_indent_right or significant_indent_left) and vertical_gap > typical_gap * 0.8:
        #    is_break = True
        elif prev_is_short and vertical_gap > typical_gap * 1.2:
            is_break = True

        # 5. Avoid false positives (continuations override weak breaks)
        #if is_continuation and not (significant_vertical_gap and prev_ends_sentence):
        #    is_break = False

        return is_break

    def set_paragraphs_intelligent(self, _df):
        df = _df.copy()
        df.sort_values(by=["page", "y0", "x0"], inplace=True)
        
        num_pages = len(df["page"].unique())
        doc_df = pd.DataFrame()

        for cur_page in range(1, num_pages + 1):
            page_df = df[df["page"] == cur_page].sort_values(by=["y0", "x0"])
            
            if page_df.empty:
                continue
            
            # Analizar estadísticas de la página
            page_stats = self._analyze_page_statistics(page_df)
            
            pages_txt = []
            paragraph_txt = []
            paragraph_bb = []
            
            cur_paragraph = 0
            previous_row = None
            previous_text = ""

            for idx, row in page_df.iterrows():
                x0, y0, x1, y1 = row["x0"], row["y0"], row["x1"], row["y1"]
                current_text = row["text"]

                # Verificar si hay salto de párrafo
                if self._is_paragraph_break(row, previous_row, page_stats, previous_text):
                    if paragraph_txt:  # Guardar párrafo anterior
                        paragraph_raw = " ".join(paragraph_txt).strip()
                        tokens = len(paragraph_raw.split())
                        x_min, y_min, x_max, y_max = self._process_boxes(paragraph_bb)
                        pages_txt.append([cur_page, cur_paragraph, paragraph_raw, tokens, x_min, y_min, x_max, y_max])
                        
                        # Reset para nuevo párrafo
                        paragraph_txt = []
                        paragraph_bb = []
                        cur_paragraph += 1

                # Agregar texto actual al párrafo
                if row["tokens"] > 0:
                    paragraph_txt.append(current_text)
                    paragraph_bb.append([x0, y0, x1, y1])

                previous_row = row
                if row["tokens"] > 0:  # Solo actualizar con texto no vacío
                    previous_text = current_text

            # Agregar último párrafo de la página
            if paragraph_txt:
                paragraph_raw = " ".join(paragraph_txt).strip()
                tokens = len(paragraph_raw.split())
                x_min, y_min, x_max, y_max = self._process_boxes(paragraph_bb)
                pages_txt.append([cur_page, cur_paragraph, paragraph_raw, tokens, x_min, y_min, x_max, y_max])

            # Guardar resultado de la página
            pages_df = pd.DataFrame(pages_txt, columns=["page", "paragraph_enum", "text", "tokens", "x0", "y0", "x1", "y1"])
            doc_df = pd.concat([doc_df, pages_df], ignore_index=True)

        # Agregar width & height
        if not doc_df.empty:
            doc_df['width'] = round(doc_df.x1 - doc_df.x0 + 0.025, 5)
            doc_df['height'] = round(doc_df.y1 - doc_df.y0 + 0.025, 5)

        return doc_df
    
    def set_paragraphs(self, df):
        df.sort_values(by=["page", "y0", "x0"], inplace=True)
        
        num_pages = len(df["page"].unique())
        doc_df = pd.DataFrame()  # all pages from this pdf

        for cur_page in range(1, num_pages + 1):
            pages_txt = []        # all paragraphs for this page 
            paragraph_txt = []    # words for current paragraph
            paragraph_bb = []     # bounding boxes for current paragraph
            
            page_df = df[df["page"] == cur_page].sort_values(by=["y0", "x0"])
            
            cur_paragraph = 0
            previous_y = None
            previous_x0 = None
            previuos_line_count = 0
            previuos_line = ""

            for idx, row in page_df.iterrows():
                x0, y0, x1, y1 = row["x0"], row["y0"], row["x1"], row["y1"]

                # --- Check for paragraph breaks ---
                paragraph_break = False

                # Rule 1: Empty line
                if row["tokens"] == 0:
                    if len(previuos_line) == 0:
                        previuos_line_count += 1
                        if previuos_line_count == 1:
                            # append empty paragraph marker
                            pages_txt.append([cur_page, -1, "", 0])
                        continue
                    else:
                        paragraph_break = True

                # Rule 2: Vertical gap > threshold, but allow same x0 to continue
                elif previous_y is not None and (y0 - previous_y) > self.LINE_GAP:
                    #if previous_x0 is None or abs(x0 - previous_x0) > self.TAP_GAP:
                        paragraph_break = True

                # --- If paragraph break, store current paragraph ---
                if paragraph_break and paragraph_txt:
                    paragraph_raw = " ".join(paragraph_txt).strip()
                    tokens = len(paragraph_raw)
                    x_min, y_min, x_max, y_max = self._process_boxes(paragraph_bb)
                    pages_txt.append([cur_page, cur_paragraph, paragraph_raw, tokens, x_min, y_min, x_max, y_max])
                    paragraph_txt = []
                    paragraph_bb = []
                    cur_paragraph += 1

                # If not a break, collect text
                if row["tokens"] > 0:
                    paragraph_txt.append(row["text"])
                    paragraph_bb.append([x0, y0, x1, y1])
                    previuos_line_count = 0  # reset empty line counter

                previuos_line = row["text"]
                previous_y = y0
                previous_x0 = x0

            # Add last paragraph of page
            if paragraph_txt:
                paragraph_raw = " ".join(paragraph_txt).strip()
                tokens = len(paragraph_raw)
                x_min, y_min, x_max, y_max = self._process_boxes(paragraph_bb)
                pages_txt.append([cur_page, cur_paragraph, paragraph_raw, tokens, x_min, y_min, x_max, y_max])

            # Save page result
            pages_df = pd.DataFrame(pages_txt, columns=["page", "paragraph_enum", "text", "tokens", "x0", "y0", "x1", "y1"])
            doc_df = pd.concat([doc_df, pages_df], ignore_index=True)

        # Add width & height
        doc_df['width'] = round(doc_df.x1 - doc_df.x0 + 0.025, 5)
        doc_df['height'] = round(doc_df.y1 - doc_df.y0 + 0.025, 5)
        
        doc_df = doc_df[doc_df["paragraph_enum"]!=-1].copy()

        return doc_df

    def filter_paragraphs(self, _df):
        df = _df.copy()
        similar_texts = []
        repeatd_ids = []
        
        df["clean_text"] = df["text"].apply(lambda x: re.sub(r"\s+", " ", x).strip())
        
        df["empty_line"] = False
        df["only_special"] = df.text.apply( lambda x: re.sub(r"[^a-zA-Z0-9\s]", "", x).strip() )
        df["only_special_len"] = df.only_special.apply( lambda x: len(x.split()))

        df['text_wo_numbers'] = df.text.str.replace('\d*', '', regex=True)
        df['text_wo_numbers_len'] = df.text_wo_numbers.apply(lambda x: len(x.split()))
    
        df['paragraph_duplicated'] = df.text_wo_numbers.duplicated(keep=False)
        
        for i, clean_text, text_wo_numbers in df[['clean_text', 'text_wo_numbers']].itertuples():
            num_paragraph = i+1
            if clean_text in similar_texts or num_paragraph in repeatd_ids:
                continue
                
            is_similar = df.text_wo_numbers.apply(lambda x: fuzz.token_set_ratio(text_wo_numbers, x) > 90)
            num_repetitions = int(np.sum(is_similar.tolist()))
            
            if self.MAX_PARAGRAPH_REPETITIONS <= num_repetitions:
                similar_texts.append(clean_text)
                ids_with = df.loc[is_similar, "paragraph_enum"].tolist()
                repeatd_ids = repeatd_ids + ids_with
                df.loc[is_similar, "repeated_with"] = num_paragraph
                df.loc[is_similar, "number_repetitions"] = len(ids_with)
                df.loc[is_similar, f'repeats_more_than_{self.MAX_PARAGRAPH_REPETITIONS}'] = True
            else:
                ids_with = df.loc[is_similar, "paragraph_enum"].tolist()
                df.loc[is_similar, "repeated_with"] = num_paragraph
                df.loc[is_similar, "number_repetitions"] = len(ids_with)
                df.loc[is_similar, f'repeats_more_than_{self.MAX_PARAGRAPH_REPETITIONS}'] = False
        
        df['has_similar'] = df.clean_text.isin(similar_texts)
        df['to_delete_paragraph'] = df.has_similar | df.paragraph_duplicated | (df.text_wo_numbers_len < self.MIN_WORDS_PER_PARAGRAPH) | df[f'repeats_more_than_{self.MAX_PARAGRAPH_REPETITIONS}']

        df_deleted = df[~df.to_delete_paragraph][["page", "paragraph_enum", "text", "clean_text", "y0", "x0", "y1", "x1"]].copy()
        df_deleted = df_deleted.reset_index(drop=True)
        
        df_deleted['width'] = abs(df_deleted.x1 - df_deleted.x0)
        df_deleted['height'] = abs(df_deleted.y1 - df_deleted.y0)

        return df_deleted
    
    def filter_paragraphs_in_bbox(self, df_, page_num, new_bbox):
        # bbox = [x, y, width, height]
        x, y, w, h = new_bbox
        x2 = x + w
        y2 = y + h
        
        df = df_[
                (df_['page'] == page_num) &
                (df_['x0'] >= x) & (df_['y0'] >= y) &
                (df_['x1'] <= x2) & (df_['y1'] <= y2)
            ].copy()
            
        df['clean_text'] = df.text.apply(lambda x : re.sub('\s+', ' ', x).strip())
        
        merged_row = pd.DataFrame({
            "page": [1],
            "paragraph_enum": [1],
            "text": [" ".join(df["text"].tolist())],
            "clean_text": [" ".join(df["clean_text"].tolist())],
        })

        return merged_row
        
        
    ############################################
    ###             Draw BBoxes              ###
    ############################################
   
    def draw_bboxes_on_pdf(self, input_pdf, df, output_pdf):
        """
        Draws bounding boxes from df onto the original PDF and saves a new PDF.
        """
        doc = fitz.open(input_pdf)

        for _, row in df.iterrows():
            page_num = int(row["page"]) - 1
            page = doc[page_num]

            rect = fitz.Rect(x0=row["x0"], y0=row["y0"], x1=row["x1"], y1=row["y1"])
            page.draw_rect(rect, color=(1, 0, 0), width=0.7)

        doc.save(output_pdf)
        doc.close()
        
        
        
