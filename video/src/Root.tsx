import { Composition } from "remotion";
import { PropertyReel } from "./PropertyReel";

export type ReelProps = {
  photos: string[];
  precio: string;
  ubicacion: string;
  tipo: string;
  operacion: string;
  recamaras?: number;
  banos?: number;
  m2?: number;
  agenteNombre: string;
  agenteTelefono: string;
  agenteEmail: string;
};

const DURATION_PER_PHOTO = 90;

export const Root: React.FC = () => {
  const dummyProps: ReelProps = {
    photos: [],
    precio: "$5,000,000 MXN",
    ubicacion: "CDMX, México",
    tipo: "Casa",
    operacion: "Venta",
    recamaras: 3,
    banos: 2,
    m2: 180,
    agenteNombre: "Agente Inmersiva",
    agenteTelefono: "5512345678",
    agenteEmail: "agente@inmersiva.com",
  };

  const numPhotos = Math.max(dummyProps.photos.length, 3);
  const totalFrames = numPhotos * DURATION_PER_PHOTO + 90;

  return (
    <Composition
      id="PropertyReel"
      component={PropertyReel}
      durationInFrames={totalFrames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={dummyProps}
    />
  );
};
