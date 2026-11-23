/** Geometria normalizada (mesmas regras do servidor): x e y em [0, 1]; raio relativo à largura. */
export type Shape =
  | { kind: "rect"; x: number; y: number; w: number; h: number }
  | { kind: "circle"; cx: number; cy: number; r: number }
  | { kind: "polygon"; points: Array<[number, number]> };

export function contains(shape: Shape, x: number, y: number, aspect = 1): boolean {
  if (shape.kind === "rect") {
    return x >= shape.x && x <= shape.x + shape.w && y >= shape.y && y <= shape.y + shape.h;
  }
  if (shape.kind === "circle") {
    const dx = x - shape.cx;
    const dy = (y - shape.cy) * aspect;
    return dx * dx + dy * dy <= shape.r * shape.r;
  }
  let inside = false;
  const pts = shape.points;
  for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
    const [xi, yi] = pts[i]!;
    const [xj, yj] = pts[j]!;
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** Ponto do evento do ponteiro em coordenadas normalizadas da imagem exibida. */
export function toNormalized(clientX: number, clientY: number, rect: DOMRect): [number, number] {
  return [clamp01((clientX - rect.left) / rect.width), clamp01((clientY - rect.top) / rect.height)];
}

/** Desenha uma forma como atributos SVG no sistema `viewBox="0 0 1 aspect"`. */
export function svgProps(shape: Shape, aspect: number): Record<string, number | string> {
  if (shape.kind === "rect") return { x: shape.x, y: shape.y * aspect, width: shape.w, height: shape.h * aspect };
  if (shape.kind === "circle") return { cx: shape.cx, cy: shape.cy * aspect, r: shape.r };
  return { points: shape.points.map(([x, y]) => `${x},${y * aspect}`).join(" ") };
}
