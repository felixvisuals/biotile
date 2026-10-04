import { useTranslation } from "react-i18next";

type Titled = { title: string; title_en?: string | null };
type Described = { description?: string | null; description_en?: string | null };

/** Picks the English title/description of seeded designs on the English site; user-entered
 *  titles have no translation and are shown as written. */
export function useLocalized() {
  const { i18n } = useTranslation();
  const en = i18n.language.startsWith("en");
  return {
    title: (o: Titled) => (en && o.title_en) || o.title,
    description: (o: Described) => (en && o.description_en) || o.description,
  };
}
