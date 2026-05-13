import {
  AbsoluteFill, Sequence, useCurrentFrame,
  interpolate, Easing,
} from "remotion";
import { ReelProps } from "./Root";

const NAVY = "#1B2A4A";
const GOLD = "#C9A84C";
const FRAMES_PER_PHOTO = 90;
const CONTACT_FRAMES = 90;

const KenBurnsPhoto: React.FC<{ src: string; startFrame: number }> = ({ src, startFrame }) => {
  const frame = useCurrentFrame();
  const local = frame - startFrame;
  const scale = interpolate(local, [0, FRAMES_PER_PHOTO], [1, 1.08], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.ease),
  });
  const opacity = interpolate(local, [0, 15, FRAMES_PER_PHOTO - 15, FRAMES_PER_PHOTO], [0, 1, 1, 0]);

  return (
    <AbsoluteFill style={{ opacity }}>
      <div style={{
        width: "100%", height: "100%",
        backgroundImage: `url(data:image/jpeg;base64,${src})`,
        backgroundSize: "cover", backgroundPosition: "center",
        transform: `scale(${scale})`,
      }} />
      <AbsoluteFill style={{
        background: "linear-gradient(to bottom, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0.7) 100%)",
      }} />
    </AbsoluteFill>
  );
};

const PhotoSlide: React.FC<{ photo: string; index: number; props: ReelProps }> = ({ photo, index, props }) => {
  const frame = useCurrentFrame();
  const textOpacity = interpolate(frame, [20, 40], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const textY = interpolate(frame, [20, 40], [30, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      <KenBurnsPhoto src={photo} startFrame={0} />
      {index === 0 && (
        <AbsoluteFill style={{ display: "flex", flexDirection: "column", justifyContent: "flex-end", padding: "80px 60px" }}>
          <div style={{ opacity: textOpacity, transform: `translateY(${textY}px)` }}>
            <div style={{
              background: GOLD, color: NAVY,
              display: "inline-block", padding: "8px 20px",
              borderRadius: 4, fontSize: 32, fontWeight: 700,
              letterSpacing: 2, marginBottom: 20,
            }}>
              EN {props.operacion.toUpperCase()}
            </div>
            <div style={{ color: GOLD, fontSize: 72, fontWeight: 700, lineHeight: 1 }}>
              {props.precio}
            </div>
            <div style={{ color: "white", fontSize: 38, marginTop: 12 }}>
              📍 {props.ubicacion}
            </div>
            <div style={{ display: "flex", gap: 30, marginTop: 20 }}>
              {props.recamaras && <span style={{ color: "white", fontSize: 34 }}>🛏 {props.recamaras} rec.</span>}
              {props.banos && <span style={{ color: "white", fontSize: 34 }}>🚿 {props.banos} baños</span>}
              {props.m2 && <span style={{ color: "white", fontSize: 34 }}>📐 {props.m2}m²</span>}
            </div>
          </div>
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

const ContactScreen: React.FC<{ p: ReelProps }> = ({ p }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{
      background: NAVY, opacity,
      display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: 80,
    }}>
      <div style={{ color: GOLD, fontSize: 24, letterSpacing: 4, textTransform: "uppercase", marginBottom: 40 }}>
        INMERSIVA GRUPO INMOBILIARIO
      </div>
      <div style={{ color: "white", fontSize: 52, fontWeight: 700, textAlign: "center", marginBottom: 20 }}>
        {p.agenteNombre}
      </div>
      <div style={{ color: GOLD, fontSize: 38, marginBottom: 12 }}>📱 {p.agenteTelefono}</div>
      <div style={{ color: "white", fontSize: 32, opacity: 0.8 }}>✉️ {p.agenteEmail}</div>
      <div style={{ marginTop: 60, color: GOLD, fontSize: 26 }}>inmobiliariainmersiva.com</div>
    </AbsoluteFill>
  );
};

export const PropertyReel: React.FC<ReelProps> = (props) => {
  const photos = props.photos.length > 0 ? props.photos : [""];
  return (
    <AbsoluteFill style={{ background: "black", fontFamily: "'Helvetica Neue', Arial, sans-serif" }}>
      {photos.map((photo, i) => (
        <Sequence key={i} from={i * FRAMES_PER_PHOTO} durationInFrames={FRAMES_PER_PHOTO}>
          <PhotoSlide photo={photo} index={i} props={props} />
        </Sequence>
      ))}
      <Sequence from={photos.length * FRAMES_PER_PHOTO} durationInFrames={CONTACT_FRAMES}>
        <ContactScreen p={props} />
      </Sequence>
    </AbsoluteFill>
  );
};
