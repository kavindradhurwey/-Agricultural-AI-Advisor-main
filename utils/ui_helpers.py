import streamlit as st
import time
import base64
from typing import List, Dict, Any

class UIHelpers:
    """
    UI helper functions for enhanced user experience
    """
    
    def __init__(self):
        pass
    
    def display_typing_effect(self, text: str, delay: float = 0.03):
        """Display text with typing animation effect"""
        placeholder = st.empty()
        displayed_text = ""
        
        for char in text:
            displayed_text += char
            placeholder.markdown(f'<div class="typing-animation">{displayed_text}</div>', unsafe_allow_html=True)
            time.sleep(delay)
        
        # Final display without cursor
        placeholder.markdown(displayed_text)
    
    def create_metric_card(self, title: str, value: str, delta: str = None, color: str = "#4CAF50"):
        """Create a custom metric card"""
        delta_html = f'<p style="color: {color}; font-size: 14px; margin: 0;">{delta}</p>' if delta else ""
        
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(240,248,255,0.9) 100%);
            padding: 20px;
            border-radius: 10px;
            border-left: 4px solid {color};
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin: 10px 0;
        ">
            <h3 style="color: #333; margin: 0; font-size: 16px;">{title}</h3>
            <h2 style="color: {color}; margin: 5px 0; font-size: 28px;">{value}</h2>
            {delta_html}
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
    
    def create_alert_box(self, message: str, alert_type: str = "info"):
        """Create styled alert boxes"""
        color_map = {
            "info": "#2196F3",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336"
        }
        
        bg_color_map = {
            "info": "#E3F2FD",
            "success": "#E8F5E8",
            "warning": "#FFF3E0",
            "error": "#FFEBEE"
        }
        
        color = color_map.get(alert_type, "#2196F3")
        bg_color = bg_color_map.get(alert_type, "#E3F2FD")
        
        alert_html = f"""
        <div style="
            background: {bg_color};
            border-left: 4px solid {color};
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        ">
            <p style="margin: 0; color: #333;">{message}</p>
        </div>
        """
        
        st.markdown(alert_html, unsafe_allow_html=True)
    
    def create_progress_bar(self, progress: float, text: str = ""):
        """Create a custom progress bar"""
        progress_html = f"""
        <div style="margin: 20px 0;">
            <p style="margin-bottom: 5px; color: #333;">{text}</p>
            <div style="
                width: 100%;
                background-color: #e0e0e0;
                border-radius: 25px;
                height: 8px;
                overflow: hidden;
            ">
                <div style="
                    width: {progress}%;
                    background: linear-gradient(90deg, #4CAF50 0%, #81C784 100%);
                    height: 100%;
                    border-radius: 25px;
                    transition: width 0.3s ease;
                "></div>
            </div>
        </div>
        """
        
        st.markdown(progress_html, unsafe_allow_html=True)
    
    def create_feature_card(self, icon: str, title: str, description: str, color: str = "#4CAF50"):
        """Create feature showcase cards"""
        card_html = f"""
        <div style="
            background: linear-gradient(135deg, rgba(255,255,255,0.95) 0%, rgba(248,255,248,0.95) 100%);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-top: 3px solid {color};
            margin: 15px 0;
            transition: transform 0.3s ease;
        ">
            <div style="font-size: 40px; margin-bottom: 15px;">{icon}</div>
            <h3 style="color: {color}; margin-bottom: 10px; font-size: 20px;">{title}</h3>
            <p style="color: #666; line-height: 1.6; margin: 0;">{description}</p>
        </div>
        """
        
        st.markdown(card_html, unsafe_allow_html=True)
    
    def create_timeline_item(self, title: str, description: str, timestamp: str = ""):
        """Create timeline items for chat history"""
        timeline_html = f"""
        <div style="
            border-left: 3px solid #4CAF50;
            padding-left: 20px;
            margin: 15px 0;
            position: relative;
        ">
            <div style="
                position: absolute;
                left: -8px;
                top: 0;
                width: 12px;
                height: 12px;
                background: #4CAF50;
                border-radius: 50%;
            "></div>
            <h4 style="color: #333; margin: 0 0 5px 0; font-size: 16px;">{title}</h4>
            <p style="color: #666; margin: 0 0 5px 0; font-size: 14px;">{description}</p>
            {f'<small style="color: #999;">{timestamp}</small>' if timestamp else ''}
        </div>
        """
        
        st.markdown(timeline_html, unsafe_allow_html=True)
    
    def create_badge(self, text: str, color: str = "#4CAF50"):
        """Create colored badges"""
        badge_html = f"""
        <span style="
            background: {color};
            color: white;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin: 2px;
            display: inline-block;
        ">{text}</span>
        """
        
        st.markdown(badge_html, unsafe_allow_html=True)
    
    def create_data_table(self, data: List[Dict], headers: List[str]):
        """Create a styled data table"""
        # Generate table rows
        rows_html = ""
        for row in data:
            row_html = "<tr>"
            for header in headers:
                value = row.get(header, "")
                row_html += f"<td style='padding: 12px; border-bottom: 1px solid #eee;'>{value}</td>"
            row_html += "</tr>"
            rows_html += row_html
        
        # Generate headers
        headers_html = "<tr>"
        for header in headers:
            headers_html += f"<th style='padding: 12px; background: #f5f5f5; border-bottom: 2px solid #4CAF50; text-align: left;'>{header}</th>"
        headers_html += "</tr>"
        
        table_html = f"""
        <table style="
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        ">
            <thead>{headers_html}</thead>
            <tbody>{rows_html}</tbody>
        </table>
        """
        
        st.markdown(table_html, unsafe_allow_html=True)
    
    def display_weather_widget(self, weather_data: Dict):
        """Display weather information in a widget format"""
        if not weather_data:
            return
        
        current = weather_data.get('current', {})
        location = weather_data.get('location', {})
        
        widget_html = f"""
        <div style="
            background: linear-gradient(135deg, #87CEEB 0%, #98D8E8 100%);
            border-radius: 20px;
            padding: 25px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            margin: 20px 0;
        ">
            <h2 style="margin: 0 0 10px 0; font-size: 24px;">📍 {location.get('name', 'Unknown')}</h2>
            <div style="font-size: 48px; margin: 20px 0;">{current.get('temp_c', 0)}°C</div>
            <p style="font-size: 18px; margin: 10px 0;">{current.get('condition', {}).get('text', 'Unknown')}</p>
            <div style="display: flex; justify-content: space-between; margin-top: 20px;">
                <div>
                    <div>💧 {current.get('humidity', 0)}%</div>
                    <small>Humidity</small>
                </div>
                <div>
                    <div>💨 {current.get('wind_kph', 0)} km/h</div>
                    <small>Wind</small>
                </div>
                <div>
                    <div>👁️ {current.get('vis_km', 0)} km</div>
                    <small>Visibility</small>
                </div>
            </div>
        </div>
        """
        
        st.markdown(widget_html, unsafe_allow_html=True)
    
    def create_loading_spinner(self, text: str = "Loading..."):
        """Create a custom loading spinner"""
        spinner_html = f"""
        <div style="text-align: center; margin: 40px 0;">
            <div style="
                border: 4px solid #f3f3f3;
                border-top: 4px solid #4CAF50;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px auto;
            "></div>
            <p style="color: #666; font-size: 16px;">{text}</p>
        </div>
        
        <style>
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
        </style>
        """
        
        st.markdown(spinner_html, unsafe_allow_html=True)
