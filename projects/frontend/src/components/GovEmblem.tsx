/**
 * 정부 상징 엠블럼 — 대한민국 정부 공식 상징 SVG를 그대로 쓴다.
 * `public/gov-emblem.svg`가 원본이다. 브랜드 텍스트가 기관명을 읽히므로 스크린리더에서 감춘다.
 */
export function GovEmblem({ className }: { className?: string }) {
  return (
    <img
      src="/gov-emblem.svg"
      alt=""
      aria-hidden="true"
      width={36}
      height={36}
      className={className}
    />
  );
}
