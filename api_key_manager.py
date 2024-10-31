import streamlit as st
import os
from typing import Optional


class APIKeyManager:
    @staticmethod
    def get_api_key() -> Optional[str]:
        """Get Stability API key from various sources"""
        if 'STABILITY_API_KEY' in st.secrets:
            return st.secrets['STABILITY_API_KEY']
        if 'stability_api_key' in st.session_state:
            return st.session_state.stability_api_key
        return os.getenv('STABILITY_API_KEY')
    
    @staticmethod
    def setup_api_key_ui():
        """Display API key input in sidebar and stop until key is provided"""
        api_key = APIKeyManager.get_api_key()
        
        if api_key:
            return True
        
        # Show input field only if no key exists
        st.sidebar.title("API Key Setup")
        new_api_key = st.sidebar.text_input(
            "Enter your Stability AI API key",
            type="password",
            help="Get your API key from https://platform.stability.ai/"
        )
        
        if new_api_key:
            st.session_state.stability_api_key = new_api_key
            os.environ['STABILITY_API_KEY'] = new_api_key
            st.sidebar.success("API key saved!")
            return True
        
        st.sidebar.warning("Please enter your Stability AI API key")
        st.stop()  # Stop execution until key is provided