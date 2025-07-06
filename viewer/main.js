// viewer/main.js
import * as THREE from 'https://cdn.skypack.dev/three@0.128.0';
import { GLTFLoader } from 'https://cdn.skypack.dev/three@0.128.0/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'https://cdn.skypack.dev/three@0.128.0/examples/jsm/controls/OrbitControls.js';
import { io } from 'https://cdn.socket.io/4.7.2/socket.io.esm.min.js';

// WebSocket connection and GLTF loader
const socket = io();
const loader = new GLTFLoader();
let scene, camera, renderer, controls, model;

// Basic Three.js setup
scene = new THREE.Scene();
camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
renderer = new THREE.WebGLRenderer({ antialias: true });

renderer.setSize(window.innerWidth, window.innerHeight);
document.body.appendChild(renderer.domElement);
camera.position.set(0, 1, 5);

// Camera controls
controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;

// Lighting setup 
scene.add(new THREE.AmbientLight(0x404040, 0.6));

const mainLight = new THREE.DirectionalLight(0xffffff, 1.0);
mainLight.position.set(10, 10, 5);
scene.add(mainLight);

const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
fillLight.position.set(-5, 0, -5);
scene.add(fillLight);

// Dark background instead of default white
scene.background = new THREE.Color(0x2a2a2a);

// Handle window resize
window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});

// Load the most recent GLB file from server
async function loadLatestModel() {
    const infoDiv = document.getElementById('model-info');
    
    try {
        const response = await fetch('/latest-model');
        const { filename } = await response.json();
        
        if (!filename) {
            console.log('No GLB files found');
            return;
        }
        
        // Get file size from server
        const fileResponse = await fetch(`/blender_exports/${filename}`, { method: 'HEAD' });
        const fileSize = (parseInt(fileResponse.headers.get('content-length')) / 1024).toFixed(1);
        
        // Remove old model if it exists
        if (model) {
            scene.remove(model);
        }
        
        // Load new model with timing
        const startTime = performance.now();
        loader.load(
            `/blender_exports/${filename}`,
            (gltf) => {
                const loadTime = ((performance.now() - startTime) / 1000).toFixed(2);
                model = gltf.scene;
                scene.add(model);
                
                // Auto-frame the model in the viewport
                const box = new THREE.Box3().setFromObject(model);
                const center = box.getCenter(new THREE.Vector3());
                
                // Point camera controls at model center
                controls.target.copy(center);
                controls.update();
                
                // Position camera to fit entire model
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const distance = maxDim * 1.5; // Give some breathing room
                
                camera.position.copy(center);
                camera.position.add(new THREE.Vector3(distance, distance * 0.4, distance));
                camera.lookAt(center);
                
                // Show info in top-right corner
                infoDiv.innerHTML = `
                    <div>File: ${filename}</div>
                    <div>Size: ${fileSize} KB</div>
                    <div>Load Time: ${loadTime}s</div>
                `;
                infoDiv.style.display = 'block';
                
                console.log(`Loaded: ${filename} (${loadTime}s)`);
            },
            (progress) => {
                const percent = (progress.loaded / progress.total * 100).toFixed(1);
                console.log(`Loading progress: ${percent}%`);
            },
            (error) => {
                console.error('Failed to load model:', error);
            }
        );
    } catch (error) {
        console.error('Failed to fetch latest model:', error);
    }
}

// Listen for model updates from server
socket.on('model_updated', () => {
    console.log('Model updated - reloading...');
    // Small delay to ensure file write is complete
    setTimeout(loadLatestModel, 1000);
});

// Load initial model
loadLatestModel();

// Main render loop
function animate() {
    requestAnimationFrame(animate);
    controls.update(); // Smooth camera movement
    renderer.render(scene, camera);
}

animate();