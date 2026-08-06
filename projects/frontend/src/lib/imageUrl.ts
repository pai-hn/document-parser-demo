/** API가 반환한 imageUrl을 브라우저에서 쓸 수 있는 경로로 정규화한다. */
export function resolveImageUrl(imageUrl: string): string {
  if (
    imageUrl.startsWith("blob:") ||
    imageUrl.startsWith("http://") ||
    imageUrl.startsWith("https://") ||
    imageUrl.startsWith("/samples/")
  ) {
    return imageUrl;
  }
  if (imageUrl.startsWith("/api/")) {
    return imageUrl;
  }
  if (imageUrl.startsWith("/")) {
    return `/api${imageUrl}`;
  }
  return imageUrl;
}
