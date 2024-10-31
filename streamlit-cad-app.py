from api_key_manager import APIKeyManager

import streamlit as st
import numpy as np
from PIL import Image
import plotly.graph_objects as go
import tempfile
import os
import requests
from typing import Tuple
import logging
from openai import OpenAI
import base64
from io import BytesIO
import trimesh
import streamlit.components.v1 as components
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StabilityAI3DGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.stability.ai/v2beta/3d/stable-fast-3d"
    
    def generate_3d_model(self, image: Image.Image, params: dict) -> bytes:
        """Generate 3D model from image using Stability AI API"""
        try:
            # Convert PIL Image to bytes
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Make API request
            response = requests.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                files={
                    "image": img_byte_arr
                },
                data=params
            )
            
            # Log response status
            logger.info(f"Stability AI API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                return response.content
            else:
                error_msg = response.json().get('message', str(response.json()))
                logger.error(f"API Error: {error_msg}")
                raise Exception(f"API Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error in 3D generation: {str(e)}")
            raise

def create_model_viewer_html(model_data: bytes) -> str:
    """Create HTML for the 3D model viewer using base64 encoded data"""
    base64_model = base64.b64encode(model_data).decode('utf-8')
    blob_url = f"data:model/gltf-binary;base64,{base64_model}"
    
    return f"""
        <script type="module" src="https://unpkg.com/@google/model-viewer@3.4.0/dist/model-viewer.min.js"></script>
        <style>
            model-viewer {{
                width: 100%;
                height: 400px;
                background-color: #f0f0f0;
                margin: 0 auto;
            }}
            .container {{
                display: flex;
                justify-content: center;
                width: 100%;
                max-width: 800px;
                margin: 0 auto;
            }}
        </style>
        <div class="container">
            <model-viewer
                src="{blob_url}"
                auto-rotate
                camera-controls
                shadow-intensity="1"
                shadow-softness="1"
                exposure="0.75"
                environment-image="neutral"
                auto-rotate-delay="0"
                rotation-per-second="30deg"
                interaction-prompt="auto"
                ar
                style="width: 100%; height: 400px;"
            ></model-viewer>
        </div>
    """

def convert_glb_to_stl(glb_data: bytes) -> bytes:
    """Convert GLB data to STL format"""
    try:
        # Create a temporary file for the GLB data
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp_glb:
            tmp_glb.write(glb_data)
            tmp_glb.flush()
            
            # Load the GLB file with trimesh
            mesh = trimesh.load(tmp_glb.name)
            
            # Export as STL to a bytes buffer
            stl_buffer = BytesIO()
            mesh.export(stl_buffer, file_type='stl')
            
            # Clean up temporary file
            os.unlink(tmp_glb.name)
            
            return stl_buffer.getvalue()
            
    except Exception as e:
        logger.error(f"Error converting GLB to STL: {str(e)}")
        raise

def main():
    st.set_page_config(page_title="Stability AI 3D Generator", layout="wide")

    # Setup API key first
    if not APIKeyManager.setup_api_key_ui():
        st.error("Please provide a Stability AI API key in the sidebar to use the application.")
        st.stop()
    
    st.title("Image to 3D Model Generator")
    st.write("Upload an image to generate a 3D model using Stability AI Stable Fast 3D")
    
    # Initialize the generator
    if 'generator' not in st.session_state:
        api_key = APIKeyManager.get_api_key()
        st.session_state.generator = StabilityAI3DGenerator(api_key)
    
    # Create columns for parameters
    col1, col2 = st.columns(2)
    
    with col1:
        # Remesh radio buttons
        remesh_option = st.radio(
            "Remesh Algorithm",
            options=["none", "quad", "triangle"],
            index=0,
            help="Controls the remeshing algorithm used to generate the 3D model"
        )
        
        # Vertex count slider
        vertex_count = st.slider(
            "Vertex Count",
            min_value=-1,
            max_value=20000,
            value=-1,
            help="Number of vertices in the simplified mesh. -1 means no limit."
        )
    
    with col2:
        # Foreground ratio slider
        foreground_ratio = st.slider(
            "Foreground Ratio",
            min_value=0.1,
            max_value=1.0,
            value=0.85,
            step=0.05,
            help="Controls the amount of padding around the object. Higher value means less padding."
        )
    
    # File uploader
    uploaded_file = st.file_uploader("Choose an image file", type=['jpg', 'jpeg', 'png'])
    
    if uploaded_file is not None:
        try:
            # Load and display the image
            image = Image.open(uploaded_file)
            
            st.image(image, caption='Input Image', use_column_width=True)
            
            # Process button
            if st.button('Generate 3D Model'):
                with st.spinner('Generating 3D model... This may take a minute...'):
                    try:
                        # Prepare parameters
                        params = {
                            'remesh': remesh_option,
                            'vertex_count': vertex_count,
                            'foreground_ratio': foreground_ratio
                        }
                        
                        # Remove vertex_count if it's -1 (default)
                        if vertex_count == -1:
                            params.pop('vertex_count')
                        
                        # Generate 3D model
                        model_data = st.session_state.generator.generate_3d_model(image, params)
                        
                        # Display 3D viewer
                        st.subheader("3D Model Viewer")
                        components.html(
                            create_model_viewer_html(model_data),
                            height=450
                        )
                        
                        # Create download buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # GLB download
                            st.download_button(
                                label="Download GLB Model",
                                data=model_data,
                                file_name="generated_model.glb",
                                mime="model/gltf-binary"
                            )
                        
                        with col2:
                            # Convert and provide STL download
                            try:
                                stl_data = convert_glb_to_stl(model_data)
                                st.download_button(
                                    label="Download STL Model",
                                    data=stl_data,
                                    file_name="generated_model.stl",
                                    mime="model/stl"
                                )
                            except Exception as e:
                                st.error(f"Error converting to STL: {str(e)}")
                        
                        st.success("3D model generated successfully! Use the viewer above to inspect the model and the buttons to download in your preferred format.")
                        
                    except Exception as e:
                        st.error(f"Error generating 3D model: {str(e)}")
                        logger.error(f"Generation error: {str(e)}")
        
        except Exception as e:
            st.error(f"Error loading image: {str(e)}")
            logger.error(f"Image loading error: {str(e)}")
    
    # Instructions
    with st.expander("How to use"):
        st.write("""
        1. Enter your Stability AI API key in the sidebar
        2. Upload a clear image of an object
        3. Adjust the generation parameters if needed:
           - Remesh Algorithm: Controls how the 3D model is constructed
           - Vertex Count: Controls the complexity of the model (-1 for no limit)
           - Foreground Ratio: Controls padding around the object (0.85 is optimal for most cases)
        4. Click 'Generate 3D Model' to process the image
        5. Use the 3D viewer to inspect the generated model:
           - Click and drag to rotate
           - Scroll to zoom
           - Right-click and drag to pan
        6. Download the model in either GLB or STL format:
           - GLB: Best for web viewing and animation
           - STL: Better for 3D printing
        
        Best practices for input images:
        - Use clear, well-lit photos
        - Ensure the object is centered
        - Use images with simple backgrounds
        - Avoid highly reflective or transparent objects
        """)

if __name__ == "__main__":
    main()