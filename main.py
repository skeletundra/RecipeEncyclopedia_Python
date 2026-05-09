import customtkinter as ctk
import tkinter as tk
import sqlite3
import json
import os
import traceback
import shutil
from tkinter import filedialog
from PIL import Image

# -----
# database and file logic
# -----

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECIPE_DIR = os.path.join(BASE_DIR, "recipes")
DB_PATH = os.path.join(BASE_DIR, "recipes.db")

def init_system():
    if not os.path.exists(RECIPE_DIR):
        os.makedirs(RECIPE_DIR)
        
    img_path = os.path.join(RECIPE_DIR, "placeholder.png")
    if not os.path.exists(img_path):
        img = Image.new("RGB", (400, 300), color=(80, 80, 80))
        img.save(img_path)
        
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("""CREATE TABLE IF NOT EXISTS recipes (
        id INTEGER PRIMARY KEY,
        title TEXT,
        tags TEXT,
        ingredients TEXT,
        instructions TEXT,
        notes TEXT,
        image_path TEXT
    )""")
    
    c.execute("""CREATE TABLE IF NOT EXISTS tags (
        name TEXT UNIQUE
    )""")
    
    # clear recipe cache to rebuild from local files
    c.execute("DELETE FROM recipes")
    
    for filename in os.listdir(RECIPE_DIR):
        if filename.endswith(".json"):
            filepath = os.path.join(RECIPE_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    recipe = json.load(f)
                    
                c.execute("INSERT INTO recipes (title, tags, ingredients, instructions, notes, image_path) VALUES (?, ?, ?, ?, ?, ?)",
                          (recipe.get("title", ""), recipe.get("tags", ""), recipe.get("ingredients", ""), 
                           recipe.get("instructions", ""), recipe.get("notes", ""), recipe.get("image_path", "")))
                
                # auto register tags found in the files
                tags_str = recipe.get("tags", "")
                if tags_str:
                    for t in tags_str.split(","):
                        t = t.strip().title()
                        if t:
                            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (t,))
            except Exception as e:
                print(f"failed to load {filename}: {e}")
    
    conn.commit()
    conn.close()

# -----
# global accessibility and keyboard navigation helper
# -----
def global_arrow_nav(event):
    focused = event.widget.focus_get()
    if not focused:
        return
    
    if isinstance(focused, (tk.Entry, tk.Text)):
        return

    if event.keysym in ("Up", "Left"):
        focused.tk_focusPrev().focus_set()
        return "break"
    elif event.keysym in ("Down", "Right"):
        focused.tk_focusNext().focus_set()
        return "break"

def bind_accessibility(widget, command=None):
    def on_focus_in(event):
        if isinstance(widget, ctk.CTkButton):
            if not hasattr(widget, "_orig_fg"):
                widget._orig_fg = widget.cget("fg_color")
            try:
                widget.configure(fg_color=widget.cget("hover_color"))
            except:
                pass
        elif isinstance(widget, ctk.CTkCheckBox):
            if not hasattr(widget, "_orig_text_color"):
                widget._orig_text_color = widget.cget("text_color")
            widget.configure(text_color="#3B8ED0")

    def on_focus_out(event):
        if isinstance(widget, ctk.CTkButton):
            if hasattr(widget, "_orig_fg"):
                widget.configure(fg_color=widget._orig_fg)
        elif isinstance(widget, ctk.CTkCheckBox):
            if hasattr(widget, "_orig_text_color"):
                widget.configure(text_color=widget._orig_text_color)

    def on_return(event):
        if command:
            command()
        on_focus_out(None)

    widget.bind("<FocusIn>", on_focus_in)
    widget.bind("<FocusOut>", on_focus_out)
    
    if command:
        widget.bind("<Return>", on_return)

# -----
# tooltip class
# -----
class ToolTip:
    _active_tooltip = None

    def __init__(self, widget, text, delay=400):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.schedule_id = None
        
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.widget.bind("<ButtonPress>", self.hide_tooltip)
        self.widget.bind("<Destroy>", self.hide_tooltip)

    def schedule_tooltip(self, event):
        self.hide_tooltip()
        self.x = event.x_root + 15
        self.y = event.y_root + 10
        self.schedule_id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self):
        if ToolTip._active_tooltip:
            ToolTip._active_tooltip.hide_tooltip()
        ToolTip._active_tooltip = self

        self.tooltip_window = ctk.CTkToplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{self.x}+{self.y}")
        self.tooltip_window.attributes("-topmost", True)
        
        label = ctk.CTkLabel(self.tooltip_window, text=self.text, fg_color="#333333", 
                             text_color="white", corner_radius=4, padx=10, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.schedule_id:
            self.widget.after_cancel(self.schedule_id)
            self.schedule_id = None
            
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            self.tooltip_window = None
            
        if ToolTip._active_tooltip == self:
            ToolTip._active_tooltip = None

# -----
# confirmation prompt classes
# -----
class DeletePrompt(ctk.CTkToplevel):
    def __init__(self, master, item_name, confirm_callback, item_type="recipe"):
        super().__init__(master)
        self.title("Confirm Deletion")
        self.geometry("450x150")
        self.resizable(False, False)
        
        self.grab_set()
        
        lbl = ctk.CTkLabel(self, text=f"Are you sure you want to delete this {item_type}:\n{item_name}?", font=("Segoe UI", 16))
        lbl.pack(pady=(30, 20))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()
        
        yes_btn = ctk.CTkButton(btn_frame, text="Yes", width=100, fg_color="#d32f2f", hover_color="#b71c1c", 
                                command=lambda: confirm_callback(item_name, self))
        yes_btn.pack(side="left", padx=10)
        bind_accessibility(yes_btn, lambda: confirm_callback(item_name, self))
        
        no_btn = ctk.CTkButton(btn_frame, text="No", width=100, command=self.destroy)
        no_btn.pack(side="right", padx=10)
        bind_accessibility(no_btn, self.destroy)
        
        no_btn.focus_set()

class OverwritePrompt(ctk.CTkToplevel):
    def __init__(self, master, recipe_title, confirm_callback):
        super().__init__(master)
        self.title("Confirm Overwrite")
        self.geometry("450x150")
        self.resizable(False, False)
        
        self.grab_set()
        
        lbl = ctk.CTkLabel(self, text=f"A recipe named '{recipe_title}' already exists.\nDo you want to overwrite it?", font=("Segoe UI", 16))
        lbl.pack(pady=(30, 20))
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack()
        
        yes_btn = ctk.CTkButton(btn_frame, text="Yes", width=100, fg_color="#d32f2f", hover_color="#b71c1c", 
                                command=lambda: confirm_callback(True, self))
        yes_btn.pack(side="left", padx=10)
        bind_accessibility(yes_btn, lambda: confirm_callback(True, self))
        
        no_btn = ctk.CTkButton(btn_frame, text="No", width=100, command=lambda: confirm_callback(False, self))
        no_btn.pack(side="right", padx=10)
        bind_accessibility(no_btn, lambda: confirm_callback(False, self))
        
        no_btn.focus_set()

# -----
# main display and ui components
# -----

class RecipeDisplay(ctk.CTkScrollableFrame):
    def __init__(self, master, recipe_data):
        super().__init__(master, fg_color="transparent")

        try:
            img_path = recipe_data.get("image_path", "")
            if not os.path.exists(img_path):
                img_path = os.path.join(RECIPE_DIR, "placeholder.png")
            img_data = Image.open(img_path)
            self.recipe_image = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(400, 300))
            self.image_label = ctk.CTkLabel(self, image=self.recipe_image, text="")
            self.image_label.pack(pady=(20, 10), anchor="center")
        except Exception as e:
            print(f"image load error: {e}")

        self.title_label = ctk.CTkLabel(self, text=recipe_data.get("title", "Untitled"), font=("Segoe UI", 32, "bold"))
        self.title_label.pack(pady=(0, 20), anchor="center")

        self.ing_heading = ctk.CTkLabel(self, text="Ingredients:", font=("Segoe UI", 20, "bold"))
        self.ing_heading.pack(pady=(10, 5), padx=40, anchor="w")
        self.ing_label = ctk.CTkLabel(self, text=recipe_data.get("ingredients", ""), font=("Segoe UI", 16), justify="left")
        self.ing_label.pack(pady=0, padx=60, anchor="w")

        self.inst_heading = ctk.CTkLabel(self, text="Instructions:", font=("Segoe UI", 20, "bold"))
        self.inst_heading.pack(pady=(30, 5), padx=40, anchor="w")
        self.inst_label = ctk.CTkLabel(self, text=recipe_data.get("instructions", ""), font=("Segoe UI", 16), justify="left", wraplength=500)
        self.inst_label.pack(pady=(0, 40), padx=60, anchor="w")

        if recipe_data.get("notes") and recipe_data["notes"].strip() != "":
            self.notes_heading = ctk.CTkLabel(self, text="Notes:", font=("Segoe UI", 20, "bold"))
            self.notes_heading.pack(pady=(10, 5), padx=40, anchor="w")
            self.notes_label = ctk.CTkLabel(self, text=recipe_data["notes"], font=("Segoe UI", 16), justify="left", wraplength=500)
            self.notes_label.pack(pady=(0, 40), padx=60, anchor="w")

class WelcomeScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.title_label = ctk.CTkLabel(self, text="Welcome to the Recipe Encyclopedia", font=("Segoe UI", 32, "bold"))
        self.title_label.pack(pady=(60, 10))
        
        self.subtitle_label = ctk.CTkLabel(self, text="Your personal, offline culinary content management system.", font=("Segoe UI", 18))
        self.subtitle_label.pack(pady=(0, 40))

        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.pack(anchor="center")

        guide_text = (
            "🔍 Searching & Filtering\n"
            "• Keyword Search: Type into the sidebar's search box to instantly find recipes by title.\n"
            "• Categories: Expand the dropdown to filter by tags. Selecting multiple tags will show only\n"
            "  recipes that contain ALL selected tags (e.g., checking 'Dinner' and 'Vegan' shows vegan dinners).\n\n"
            
            "📝 Managing Content\n"
            "• Manage Recipes: Click the top bar button to create new recipe cards. You can upload custom images\n"
            "  and write detailed instructions. To delete a recipe, click its title inside the management menu.\n"
            "• Manage Tags: Click the top bar button to add new custom tags to organize your growing collection.\n\n"
            
            "⌨️ Accessibility & Controls\n"
            "• Keyboard Navigation: Use the Tab key, all four Arrow keys, and Enter key to smoothly navigate\n"
            "  through the menus, buttons, and checkboxes without ever needing to touch your mouse.\n"
            "• Display: Use the 'Toggle Theme' button in the top right to switch between Light and Dark mode."
        )

        self.usage_label = ctk.CTkLabel(self.info_frame, text=guide_text, font=("Segoe UI", 15), justify="left")
        self.usage_label.pack(pady=10, padx=20)

# -----
# manage tags window
# -----

class ManageTagsWindow(ctk.CTkToplevel):
    def __init__(self, master, refresh_callback):
        super().__init__(master)
        self.title("Manage Tags")
        self.geometry("400x550")
        self.refresh_callback = refresh_callback
        
        self.grab_set()

        self.add_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.add_frame.pack(pady=20, padx=20, fill="x")

        self.new_tag_var = ctk.StringVar()
        self.new_tag_entry = ctk.CTkEntry(self.add_frame, textvariable=self.new_tag_var, placeholder_text="New tag name...")
        self.new_tag_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.add_btn = ctk.CTkButton(self.add_frame, text="Add", width=60, command=self.add_tag)
        self.add_btn.pack(side="right")
        bind_accessibility(self.add_btn, self.add_tag)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search tags...")
        self.search_entry.pack(pady=(0, 10), padx=20, fill="x")
        self.search_entry.bind("<KeyRelease>", self.populate_list)

        self.tag_list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.tag_list_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.populate_list()

    def add_tag(self):
        tag = self.new_tag_var.get().strip().title().replace(",", "")
        if tag:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            c.execute("SELECT 1 FROM tags WHERE LOWER(name) = ?", (tag.lower(),))
            if c.fetchone():
                self.new_tag_var.set("")
                self.new_tag_entry.configure(placeholder_text="Error: Tag already exists!")
                conn.close()
                return
                
            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            conn.commit()
            conn.close()
            
            self.new_tag_entry.configure(placeholder_text="New tag name...")
            self.new_tag_var.set("")
            self.populate_list()
            self.refresh_callback()

    def populate_list(self, event=None):
        for widget in self.tag_list_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().lower()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM tags ORDER BY name ASC")
        all_tags = c.fetchall()
        conn.close()

        for row in all_tags:
            tag = row[0]
            if search_query in tag.lower():
                item_frame = ctk.CTkFrame(self.tag_list_frame, fg_color="transparent")
                item_frame.pack(fill="x", pady=5)
                
                x_label = ctk.CTkLabel(item_frame, text="X", text_color="#d32f2f", font=("Segoe UI", 16, "bold"))
                x_label.pack(side="left", padx=(5, 10))
                
                title_btn = ctk.CTkButton(item_frame, text=tag, fg_color="transparent", 
                                          text_color=("gray10", "gray90"), anchor="w",
                                          hover_color=("gray70", "gray30"),
                                          command=lambda t=tag: self.prompt_delete(t))
                title_btn.pack(side="left", fill="x", expand=True)
                bind_accessibility(title_btn, lambda t=tag: self.prompt_delete(t))

    def prompt_delete(self, tag):
        DeletePrompt(self, tag, self.execute_delete, item_type="tag")

    def execute_delete(self, tag, prompt_window):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM tags WHERE name = ?", (tag,))
        conn.commit()
        conn.close()

        prompt_window.destroy()
        self.populate_list()
        self.refresh_callback()

# -----
# management window for creating and deleting recipes
# -----

class ManageWindow(ctk.CTkToplevel):
    def __init__(self, master, refresh_callback):
        super().__init__(master)
        self.title("Manage Recipes")
        self.geometry("900x650")
        self.refresh_callback = refresh_callback
        
        self.grab_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        self.sidebar_label = ctk.CTkLabel(self.sidebar_frame, text="Delete Recipes", font=("Segoe UI", 20, "bold"))
        self.sidebar_label.pack(pady=(20, 10), padx=20)

        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self.sidebar_frame, textvariable=self.search_var, placeholder_text="Search recipes...")
        self.search_entry.pack(pady=(0, 10), padx=20, fill="x")
        self.search_entry.bind("<KeyRelease>", self.populate_sidebar)

        self.recipe_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.recipe_list_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.creator_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.creator_frame.grid(row=0, column=1, sticky="nsew")

        self.creator_title = ctk.CTkLabel(self.creator_frame, text="Create New Recipe", font=("Segoe UI", 24, "bold"))
        self.creator_title.pack(pady=(20, 20))

        self.selected_image_path = os.path.join(RECIPE_DIR, "placeholder.png")
        try:
            img_data = Image.open(self.selected_image_path)
            self.preview_image = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(200, 150))
        except:
            self.preview_image = None

        self.image_btn = ctk.CTkButton(self.creator_frame, image=self.preview_image, text="Click to Select Image", 
                                       compound="top", fg_color="transparent", border_color="gray", border_width=2, 
                                       command=self.select_image, text_color=("gray10", "gray90"))
        self.image_btn.pack(pady=10)
        bind_accessibility(self.image_btn, self.select_image)

        self.title_entry = ctk.CTkEntry(self.creator_frame, placeholder_text="Recipe Title", width=400)
        self.title_entry.pack(pady=10)

        self.tags_entry = ctk.CTkEntry(self.creator_frame, placeholder_text="Tags (comma separated, e.g. Dinner, Vegan)", width=400)
        self.tags_entry.pack(pady=10)

        self.ing_box = ctk.CTkTextbox(self.creator_frame, width=400, height=100)
        self.ing_box.pack(pady=10)
        self.apply_textbox_placeholder(self.ing_box, "Ingredients...")

        self.inst_box = ctk.CTkTextbox(self.creator_frame, width=400, height=100)
        self.inst_box.pack(pady=10)
        self.apply_textbox_placeholder(self.inst_box, "Instructions...")

        self.notes_box = ctk.CTkTextbox(self.creator_frame, width=400, height=80)
        self.notes_box.pack(pady=10)
        self.apply_textbox_placeholder(self.notes_box, "Notes (optional)...")

        self.create_btn = ctk.CTkButton(self.creator_frame, text="Create Recipe", font=("Segoe UI", 16, "bold"), command=self.create_recipe)
        self.create_btn.pack(pady=30)
        bind_accessibility(self.create_btn, self.create_recipe)

        self.populate_sidebar()

    def apply_textbox_placeholder(self, textbox, placeholder_text):
        textbox.insert("0.0", placeholder_text)
        textbox.configure(text_color="gray50")
        textbox.is_placeholder = True

        def on_focus_in(event):
            if getattr(textbox, "is_placeholder", False):
                textbox.delete("0.0", "end")
                textbox.configure(text_color=("gray10", "gray90"))
                textbox.is_placeholder = False

        def on_focus_out(event):
            content = textbox.get("0.0", "end-1c").strip()
            if not content:
                textbox.insert("0.0", placeholder_text)
                textbox.configure(text_color="gray50")
                textbox.is_placeholder = True

        textbox.bind("<FocusIn>", on_focus_in)
        textbox.bind("<FocusOut>", on_focus_out)

    def select_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            self.selected_image_path = file_path
            img_data = Image.open(self.selected_image_path)
            self.preview_image = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(200, 150))
            self.image_btn.configure(image=self.preview_image, text="Image Selected")

    def populate_sidebar(self, event=None):
        for widget in self.recipe_list_frame.winfo_children():
            widget.destroy()

        search_query = self.search_var.get().lower()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title FROM recipes")
        all_recipes = c.fetchall()
        conn.close()

        for row in all_recipes:
            title = row[0]
            if search_query in title.lower():
                item_frame = ctk.CTkFrame(self.recipe_list_frame, fg_color="transparent")
                item_frame.pack(fill="x", pady=5)
                
                x_label = ctk.CTkLabel(item_frame, text="X", text_color="#d32f2f", font=("Segoe UI", 16, "bold"))
                x_label.pack(side="left", padx=(5, 10))
                
                title_btn = ctk.CTkButton(item_frame, text=title, fg_color="transparent", 
                                          text_color=("gray10", "gray90"), anchor="w",
                                          hover_color=("gray70", "gray30"),
                                          command=lambda t=title: self.prompt_delete(t))
                title_btn.pack(side="left", fill="x", expand=True)
                bind_accessibility(title_btn, lambda t=title: self.prompt_delete(t))

    def prompt_delete(self, title):
        DeletePrompt(self, title, self.execute_delete, item_type="recipe")

    def execute_delete(self, title, prompt_window):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM recipes WHERE title = ?", (title,))
        conn.commit()
        conn.close()

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))
        filename = safe_title.replace(" ", "_").lower() + ".json"
        filepath = os.path.join(RECIPE_DIR, filename)
        if os.path.exists(filepath):
            os.remove(filepath)

        prompt_window.destroy()
        self.populate_sidebar()
        self.refresh_callback()

    def create_recipe(self):
        title = self.title_entry.get().strip()
        tags_raw = self.tags_entry.get().strip()
        
        ingredients = "" if getattr(self.ing_box, "is_placeholder", False) else self.ing_box.get("0.0", "end").strip()
        instructions = "" if getattr(self.inst_box, "is_placeholder", False) else self.inst_box.get("0.0", "end").strip()
        notes = "" if getattr(self.notes_box, "is_placeholder", False) else self.notes_box.get("0.0", "end").strip()

        if not title:
            return

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT 1 FROM recipes WHERE LOWER(title) = ?", (title.lower(),))
        exists = c.fetchone()
        conn.close()

        if exists:
            OverwritePrompt(self, title, lambda confirmed, prompt: self.finalize_recipe(
                confirmed, prompt, title, tags_raw, ingredients, instructions, notes))
        else:
            self.finalize_recipe(True, None, title, tags_raw, ingredients, instructions, notes)

    def finalize_recipe(self, confirmed, prompt_window, title, tags_raw, ingredients, instructions, notes):
        if prompt_window:
            prompt_window.destroy()
            
        if not confirmed:
            return

        tags_list =[t.strip().title() for t in tags_raw.split(",") if t.strip()]
        tags = ", ".join(tags_list)

        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-'))
        filename = safe_title.replace(" ", "_").lower() + ".json"

        final_img_path = os.path.join(RECIPE_DIR, "placeholder.png")
        if self.selected_image_path and self.selected_image_path != final_img_path:
            ext = os.path.splitext(self.selected_image_path)[1]
            new_img_name = safe_title.replace(" ", "_").lower() + ext
            final_img_path = os.path.join(RECIPE_DIR, new_img_name)
            shutil.copy(self.selected_image_path, final_img_path)

        recipe_dict = {
            "title": title, "tags": tags, "ingredients": ingredients, 
            "instructions": instructions, "notes": notes, "image_path": final_img_path
        }

        filepath = os.path.join(RECIPE_DIR, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(recipe_dict, f, indent=4)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM recipes WHERE LOWER(title) = ?", (title.lower(),))
        
        c.execute("INSERT INTO recipes (title, tags, ingredients, instructions, notes, image_path) VALUES (?, ?, ?, ?, ?, ?)",
                  (title, tags, ingredients, instructions, notes, final_img_path))
        
        for t in tags_list:
            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (t,))
            
        conn.commit()
        conn.close()

        self.title_entry.delete(0, "end")
        self.title_entry.configure(placeholder_text="Recipe Title")
        self.tags_entry.delete(0, "end")
        
        self.ing_box.delete("0.0", "end")
        self.apply_textbox_placeholder(self.ing_box, "Ingredients...")
        self.inst_box.delete("0.0", "end")
        self.apply_textbox_placeholder(self.inst_box, "Instructions...")
        self.notes_box.delete("0.0", "end")
        self.apply_textbox_placeholder(self.notes_box, "Notes (optional)...")
        
        placeholder = os.path.join(RECIPE_DIR, "placeholder.png")
        self.selected_image_path = placeholder
        try:
            img_data = Image.open(placeholder)
            self.preview_image = ctk.CTkImage(light_image=img_data, dark_image=img_data, size=(200, 150))
            self.image_btn.configure(image=self.preview_image, text="Click to Select Image")
        except:
            pass

        self.populate_sidebar()
        self.refresh_callback()

# -----
# main application controller
# -----

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        init_system()

        self.title("Recipe Encyclopedia")
        self.geometry("1000x700")
        ctk.set_appearance_mode("dark")
        
        self.bind_all("<Up>", global_arrow_nav)
        self.bind_all("<Down>", global_arrow_nav)
        self.bind_all("<Left>", global_arrow_nav)
        self.bind_all("<Right>", global_arrow_nav)
        
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        self.topbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.topbar.grid(row=0, column=0, columnspan=2, sticky="ew")
        
        self.manage_btn = ctk.CTkButton(self.topbar, text="Manage Recipes", width=140, command=self.open_manage_window)
        self.manage_btn.pack(side="left", padx=15, pady=10)
        ToolTip(self.manage_btn, "Open menu to add or remove recipes")
        bind_accessibility(self.manage_btn, self.open_manage_window)
        
        self.manage_tags_btn = ctk.CTkButton(self.topbar, text="Manage Tags", width=140, command=self.open_manage_tags_window)
        self.manage_tags_btn.pack(side="left", padx=15, pady=10)
        ToolTip(self.manage_tags_btn, "Open menu to add or remove categorical tags")
        bind_accessibility(self.manage_tags_btn, self.open_manage_tags_window)

        self.theme_btn = ctk.CTkButton(self.topbar, text="Toggle Theme", width=120, command=self.toggle_theme)
        self.theme_btn.pack(side="right", padx=15, pady=10)
        ToolTip(self.theme_btn, "Switch between light and dark mode")
        bind_accessibility(self.theme_btn, self.toggle_theme)

        self.home_btn = ctk.CTkButton(self.topbar, text="Home", width=100, command=self.show_welcome_screen)
        self.home_btn.pack(side="right", padx=(0, 15), pady=10)
        ToolTip(self.home_btn, "Return to the Welcome Screen")
        bind_accessibility(self.home_btn, self.show_welcome_screen)

        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=1, column=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        self.main_search_var = ctk.StringVar()
        self.main_search_entry = ctk.CTkEntry(self.sidebar_frame, textvariable=self.main_search_var, placeholder_text="Search recipes...")
        self.main_search_entry.pack(pady=(20, 10), padx=20, fill="x")
        self.main_search_entry.bind("<KeyRelease>", lambda e: self.filter_recipes())

        self.dropdown_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.dropdown_container.pack(pady=(10, 10), padx=20, fill="x")

        self.dropdown_open = False
        self.dropdown_btn = ctk.CTkButton(self.dropdown_container, text="Categories ▼", command=self.toggle_dropdown)
        self.dropdown_btn.pack(fill="x")
        bind_accessibility(self.dropdown_btn, self.toggle_dropdown)

        self.dropdown_content = ctk.CTkFrame(self.dropdown_container, fg_color="transparent")
        self.tag_vars = {}
        
        self.separator = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="gray30")
        self.separator.pack(fill="x", padx=20, pady=10)

        self.recipe_list_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.recipe_list_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.container = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container.grid(row=1, column=1, sticky="nsew")

        self.current_frame = None
        self.recipe_buttons =[]
        
        self.full_ui_refresh()
        self.show_welcome_screen()
        
        self.main_search_entry.focus_set()

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode()
        if current_mode == "Dark":
            ctk.set_appearance_mode("Light")
        else:
            ctk.set_appearance_mode("Dark")

    def open_manage_window(self):
        ManageWindow(self, refresh_callback=self.full_ui_refresh)
        
    def open_manage_tags_window(self):
        ManageTagsWindow(self, refresh_callback=self.full_ui_refresh)

    def full_ui_refresh(self):
        for widget in self.dropdown_content.winfo_children():
            widget.destroy()
        self.tag_vars.clear()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT name FROM tags ORDER BY name ASC")
        all_tags = c.fetchall()
        conn.close()

        for row in all_tags:
            tag = row[0]
            var = ctk.StringVar(value="")
            self.tag_vars[tag] = var
            cb = ctk.CTkCheckBox(self.dropdown_content, text=tag, variable=var, onvalue=tag, offvalue="", command=self.filter_recipes)
            cb.pack(pady=5, anchor="w")
            
            def make_toggle(c_box):
                def t():
                    c_box.toggle()
                    self.filter_recipes()
                return t
            bind_accessibility(cb, make_toggle(cb))

        self.filter_recipes()

    def clear_container(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_welcome_screen(self):
        self.clear_container()
        welcome = WelcomeScreen(self.container)
        welcome.pack(fill="both", expand=True)

    def show_recipe(self, name):
        self.clear_container()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, ingredients, instructions, notes, image_path FROM recipes WHERE title = ?", (name,))
        row = c.fetchone()
        conn.close()
        
        if row:
            data = {"title": row[0], "ingredients": row[1], "instructions": row[2], "notes": row[3], "image_path": row[4]}
            recipe_view = RecipeDisplay(self.container, data)
            recipe_view.pack(fill="both", expand=True)

    def toggle_dropdown(self):
        if self.dropdown_open:
            self.dropdown_content.pack_forget()
            self.dropdown_btn.configure(text="Categories ▼")
            self.dropdown_open = False
        else:
            self.dropdown_content.pack(fill="x", pady=(10, 0))
            self.dropdown_btn.configure(text="Categories ▲")
            self.dropdown_open = True

    def filter_recipes(self):
        for btn in self.recipe_buttons:
            btn.destroy()
        self.recipe_buttons.clear()
        
        search_query = self.main_search_var.get().lower()
        selected_tags =[var.get() for var in self.tag_vars.values() if var.get() != ""]
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT title, tags FROM recipes")
        all_recipes = c.fetchall()
        conn.close()
        
        for row in all_recipes:
            title = row[0]
            recipe_tags =[t.strip() for t in row[1].split(",")]
            
            if all(tag in recipe_tags for tag in selected_tags) and search_query in title.lower():
                btn = ctk.CTkButton(self.recipe_list_frame, text=title, command=lambda t=title: self.show_recipe(t))
                btn.pack(pady=5, padx=10, fill="x")
                self.recipe_buttons.append(btn)
                bind_accessibility(btn, lambda t=title: self.show_recipe(t))

if __name__ == "__main__":
    try:
        app = MainApp()
        app.mainloop()
    except Exception:
        traceback.print_exc()
        input("\nCRASH DETECTED. Press Enter to close.")