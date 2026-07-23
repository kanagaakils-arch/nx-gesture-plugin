import React, { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Edges } from '@react-three/drei';
import * as THREE from 'three';

export function CADModel({ 
  transform, 
  wireframe = false,
  showBase = true,
  showVertical = true,
  showPins = true,
  autoRotate = false,
  activeTool = 'Select'
}: { 
  transform: { rotation: [number, number, number], position: [number, number, number], scale: number },
  wireframe?: boolean,
  showBase?: boolean,
  showVertical?: boolean,
  showPins?: boolean,
  autoRotate?: boolean,
  activeTool?: string
}) {
  const groupRef = useRef<THREE.Group>(null);
  
  useFrame((state, delta) => {
    if (groupRef.current) {
      if (autoRotate) {
        transform.rotation[1] += delta * 0.5; // continuous slow rotation
      }

      // Smoothly interpolate to target transform
      groupRef.current.rotation.x += (transform.rotation[0] - groupRef.current.rotation.x) * 0.1;
      groupRef.current.rotation.y += (transform.rotation[1] - groupRef.current.rotation.y) * 0.1;
      groupRef.current.rotation.z += (transform.rotation[2] - groupRef.current.rotation.z) * 0.1;
      
      groupRef.current.position.x += (transform.position[0] - groupRef.current.position.x) * 0.1;
      groupRef.current.position.y += (transform.position[1] - groupRef.current.position.y) * 0.1;
      groupRef.current.position.z += (transform.position[2] - groupRef.current.position.z) * 0.1;
      
      const targetScale = transform.scale;
      groupRef.current.scale.set(
        groupRef.current.scale.x + (targetScale - groupRef.current.scale.x) * 0.1,
        groupRef.current.scale.y + (targetScale - groupRef.current.scale.y) * 0.1,
        groupRef.current.scale.z + (targetScale - groupRef.current.scale.z) * 0.1
      );
    }
  });

  return (
    <group ref={groupRef}>
      {/* Base Plate */}
      <mesh visible={showBase} castShadow receiveShadow position={[0, -0.5, 0]}>
        <boxGeometry args={[4, 0.2, 4]} />
        <meshStandardMaterial color="#64748b" metalness={0.7} roughness={0.2} wireframe={wireframe} />
        {!wireframe && <Edges scale={1} threshold={15} color="#cbd5e1" />}
      </mesh>
      
      {/* Vertical Bracket Support */}
      <mesh visible={showVertical} castShadow receiveShadow position={[-1.5, 1, 0]}>
        <boxGeometry args={[0.5, 3, 2]} />
        <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} wireframe={wireframe} />
        {!wireframe && <Edges scale={1} threshold={15} color="#94a3b8" />}
      </mesh>

      {/* Another Bracket Support */}
      <mesh visible={showVertical} castShadow receiveShadow position={[1.5, 1, 0]}>
        <boxGeometry args={[0.5, 3, 2]} />
        <meshStandardMaterial color="#475569" metalness={0.8} roughness={0.3} wireframe={wireframe} />
        {!wireframe && <Edges scale={1} threshold={15} color="#94a3b8" />}
      </mesh>

      {/* Cross Cylinder (Hole/Pin) */}
      <mesh visible={showPins} castShadow receiveShadow position={[0, 2, 0]} rotation={[0, 0, Math.PI / 2]}>
        <cylinderGeometry args={[0.4, 0.4, 4, 32]} />
        <meshStandardMaterial color="#334155" metalness={0.9} roughness={0.1} wireframe={wireframe} />
        {!wireframe && <Edges scale={1} threshold={15} color="#64748b" />}
      </mesh>

      {/* Base Mounting Holes (Visualized as small inset cylinders) */}
      {showPins && showBase && [[-1.2, 1.2], [1.2, 1.2], [-1.2, -1.2], [1.2, -1.2]].map((pos, i) => (
        <mesh key={i} position={[pos[0], -0.5, pos[1]]}>
           <cylinderGeometry args={[0.2, 0.2, 0.22, 16]} />
           <meshStandardMaterial color="#1e293b" wireframe={wireframe} />
        </mesh>
      ))}

      {/* Tool-specific visuals */}
      {activeTool === 'Sketch' && (
        <gridHelper args={[6, 20, '#005cb9', '#3e3e3e']} position={[0, 0, 0]} />
      )}
      {activeTool === 'Measure' && (
        <group position={[0, 1.5, 0]}>
          <line>
            <bufferGeometry attach="geometry" {...new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-1.5, 0, 0), new THREE.Vector3(1.5, 0, 0)])} />
            <lineBasicMaterial attach="material" color="#ef4444" linewidth={2} />
          </line>
          <mesh position={[0, 0.2, 0]}>
            <boxGeometry args={[0.8, 0.2, 0.05]} />
            <meshBasicMaterial color="#ef4444" />
          </mesh>
        </group>
      )}
      {activeTool === 'Extrude' && (
        <mesh position={[0, 3, 0]}>
          <cylinderGeometry args={[0.2, 0.2, 1, 16]} />
          <meshStandardMaterial color="#005cb9" transparent opacity={0.5} />
          <Edges scale={1} threshold={15} color="#60a5fa" />
        </mesh>
      )}
    </group>
  );
}
