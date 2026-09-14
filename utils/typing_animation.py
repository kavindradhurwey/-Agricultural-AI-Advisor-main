import streamlit as st
import time
from typing import Optional, Callable

class TypingAnimation:
    """
    Create typing animation effects for text display
    """
    
    def __init__(self, typing_speed: float = 0.03, cursor_blink: bool = True):
        self.typing_speed = typing_speed
        self.cursor_blink = cursor_blink
    
    def display_typing_text(self, text: str, container=None, delay: float = None) -> None:
        """Display text with typing animation effect"""
        try:
            if delay is None:
                delay = self.typing_speed
            
            if container is None:
                container = st.empty()
            
            displayed_text = ""
            
            # Add typing animation CSS
            typing_css = """
            <style>
            .typing-text {
                font-family: inherit;
                white-space: pre-wrap;
                word-wrap: break-word;
            }
            .typing-cursor {
                border-right: 2px solid #4CAF50;
                animation: blink-cursor 0.75s step-end infinite;
            }
            @keyframes blink-cursor {
                from, to { border-color: transparent; }
                50% { border-color: #4CAF50; }
            }
            </style>
            """
            
            st.markdown(typing_css, unsafe_allow_html=True)
            
            # Type each character
            for char in text:
                displayed_text += char
                
                if self.cursor_blink:
                    cursor_html = f'''
                    <div class="typing-text typing-cursor">{displayed_text}</div>
                    '''
                else:
                    cursor_html = f'''
                    <div class="typing-text">{displayed_text}</div>
                    '''
                
                container.markdown(cursor_html, unsafe_allow_html=True)
                time.sleep(delay)
            
            # Final display without cursor
            final_html = f'<div class="typing-text">{displayed_text}</div>'
            container.markdown(final_html, unsafe_allow_html=True)
            
        except Exception as e:
            # Fallback to regular display
            if container:
                container.write(text)
            else:
                st.write(text)
    
    def display_streaming_response(self, text_generator, container=None, prefix: str = ""):
        """Display streaming response with typing effect"""
        try:
            if container is None:
                container = st.empty()
            
            full_text = prefix
            
            for chunk in text_generator:
                full_text += chunk
                
                typing_html = f'''
                <div class="typing-text typing-cursor">{full_text}</div>
                '''
                
                container.markdown(typing_html, unsafe_allow_html=True)
                time.sleep(self.typing_speed)
            
            # Final display
            final_html = f'<div class="typing-text">{full_text}</div>'
            container.markdown(final_html, unsafe_allow_html=True)
            
        except Exception as e:
            # Fallback
            if container:
                container.write(f"{prefix}Error displaying streaming response")
            else:
                st.write(f"{prefix}Error displaying streaming response")
    
    def create_typing_placeholder(self, placeholder_text: str = "AI is thinking...") -> str:
        """Create a typing placeholder animation"""
        dots_animation_css = """
        <style>
        .typing-dots {
            display: inline-block;
        }
        .typing-dots:after {
            content: '.';
            animation: dots 1.5s steps(5, end) infinite;
        }
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60% { content: '...'; }
            90%, 100% { content: ''; }
        }
        </style>
        """
        
        placeholder_html = f'''
        {dots_animation_css}
        <div style="color: #666; font-style: italic;">
            {placeholder_text}<span class="typing-dots"></span>
        </div>
        '''
        
        return placeholder_html
    
    def display_word_by_word(self, text: str, container=None, word_delay: float = 0.2):
        """Display text word by word with animation"""
        try:
            if container is None:
                container = st.empty()
            
            words = text.split()
            displayed_words = []
            
            for word in words:
                displayed_words.append(word)
                current_text = " ".join(displayed_words)
                
                word_html = f'''
                <div class="typing-text">{current_text}<span class="typing-cursor"></span></div>
                '''
                
                container.markdown(word_html, unsafe_allow_html=True)
                time.sleep(word_delay)
            
            # Final display
            final_html = f'<div class="typing-text">{text}</div>'
            container.markdown(final_html, unsafe_allow_html=True)
            
        except Exception as e:
            if container:
                container.write(text)
            else:
                st.write(text)
    
    def create_loading_animation(self, text: str = "Loading", duration: int = 3):
        """Create a loading animation with dots"""
        loading_css = """
        <style>
        .loading-text {
            font-weight: bold;
            color: #4CAF50;
        }
        .loading-dots {
            display: inline-block;
            width: 20px;
            text-align: left;
        }
        .loading-dots:after {
            content: '';
            animation: loading 2s steps(4, end) infinite;
        }
        @keyframes loading {
            0% { content: ''; }
            25% { content: '.'; }
            50% { content: '..'; }
            75% { content: '...'; }
            100% { content: ''; }
        }
        </style>
        """
        
        loading_html = f'''
        {loading_css}
        <div class="loading-text">
            {text}<span class="loading-dots"></span>
        </div>
        '''
        
        return loading_html
    
    def display_progress_typing(self, text: str, progress_callback: Optional[Callable] = None, container=None):
        """Display text with progress indication"""
        try:
            if container is None:
                container = st.empty()
            
            total_chars = len(text)
            displayed_text = ""
            
            for i, char in enumerate(text):
                displayed_text += char
                progress = (i + 1) / total_chars
                
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(progress)
                
                progress_html = f'''
                <div>
                    <div class="typing-text typing-cursor">{displayed_text}</div>
                    <div style="margin-top: 10px;">
                        <div style="background: #e0e0e0; height: 4px; border-radius: 2px;">
                            <div style="background: #4CAF50; height: 4px; border-radius: 2px; width: {progress*100}%; transition: width 0.1s;"></div>
                        </div>
                    </div>
                </div>
                '''
                
                container.markdown(progress_html, unsafe_allow_html=True)
                time.sleep(self.typing_speed)
            
            # Final display without progress bar
            final_html = f'<div class="typing-text">{displayed_text}</div>'
            container.markdown(final_html, unsafe_allow_html=True)
            
        except Exception as e:
            if container:
                container.write(text)
            else:
                st.write(text)
    
    def create_typewriter_effect(self, text: str, container_id: str = "typewriter"):
        """Create typewriter effect with JavaScript"""
        typewriter_html = f'''
        <div id="{container_id}" style="font-family: monospace; min-height: 1.2em; border-right: 2px solid #4CAF50;"></div>
        <script>
        (function() {{
            const text = `{text}`;
            const container = document.getElementById('{container_id}');
            let i = 0;
            
            function typeWriter() {{
                if (i < text.length) {{
                    container.innerHTML += text.charAt(i);
                    i++;
                    setTimeout(typeWriter, {int(self.typing_speed * 1000)});
                }} else {{
                    container.style.borderRight = 'none';
                }}
            }}
            
            typeWriter();
        }})();
        </script>
        '''
        
        return typewriter_html
    
    def display_animated_response(self, response_parts: list, container=None, part_delay: float = 1.0):
        """Display response in animated parts"""
        try:
            if container is None:
                container = st.empty()
            
            full_response = ""
            
            for i, part in enumerate(response_parts):
                if i > 0:
                    time.sleep(part_delay)
                
                full_response += part + "\n\n"
                
                animated_html = f'''
                <div class="typing-text">
                    {full_response.replace(chr(10), '<br>')}
                    <span class="typing-cursor"></span>
                </div>
                '''
                
                container.markdown(animated_html, unsafe_allow_html=True)
            
            # Final display
            final_html = f'<div class="typing-text">{full_response.replace(chr(10), "<br>")}</div>'
            container.markdown(final_html, unsafe_allow_html=True)
            
        except Exception as e:
            if container:
                container.write("\n\n".join(response_parts))
            else:
                st.write("\n\n".join(response_parts))
