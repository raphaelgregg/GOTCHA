import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("estilos do SVG de regiões", () => {
  // Regressão: o outline global de :focus-visible, aplicado a um elemento dentro de um SVG com
  // viewBox 0..1, é medido em unidades do SVG e vira um anel gigante depois do clique.
  it("desliga o outline dos elementos focáveis dentro do SVG do Hot Area", () => {
    const css = readFileSync("src/styles.css", "utf-8");
    expect(css).toMatch(/\.hot-stage svg[^{]*:focus-visible[^{]*\{[^}]*outline:\s*none/);
  });
});
