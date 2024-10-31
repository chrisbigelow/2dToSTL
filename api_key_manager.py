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
        """Display API key input in sidebar if not already set"""
        api_key = APIKeyManager.get_api_key()
        
        if not api_key:
            st.sidebar.title("API Key Setup")
            api_key = st.sidebar.text_input(
                "Enter your Stability AI API key",
                type="password",
                help="Get your API key from https://platform.stability.ai/"
            )
            
            if api_key:
                st.session_state.stability_api_key = api_key
                os.environ['STABILITY_API_KEY'] = api_key
                st.sidebar.success("API key saved!")
            else:
                st.sidebar.warning("Please enter your Stability AI API key")
        
        return api_key is not None