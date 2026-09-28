import React from 'react';
import {
  Sparkles,
  ShoppingBag,
  Wand2,
  RefreshCw,
  Bot,
  LayoutGrid,
  CheckCircle,
  Smartphone,
  Monitor,
  Film,
  Plus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  ProductFeedItem,
  ProductSkuItem,
  CreativeMatrixResponse,
} from '@/services/ad-service';
import { toFixedSafe } from '../format-utils';
import { AdLanguage, translateAdText } from '../translations';

export interface StudioTabProps {
  productFeeds: ProductFeedItem[];
  loadingFeeds: boolean;
  selectedFeedId: string | null;
  feedItems: ProductSkuItem[];
  loadingFeedItems: boolean;
  onOpenCreateFeedModal: () => void;
  onSelectFeed: (feedId: string) => void;
  onDeleteFeed: (feedId: string) => void;
  onOpenAddSkuModal: () => void;
  matrixProductName: string;
  setMatrixProductName: (value: string) => void;
  matrixCategory: string;
  setMatrixCategory: (value: string) => void;
  matrixTargetAudience: string;
  setMatrixTargetAudience: (value: string) => void;
  matrixResult: CreativeMatrixResponse | null;
  generatingMatrix: boolean;
  onGenerateCreativeMatrix: () => void;
  currentLang?: AdLanguage;
  t?: (keyOrText: string, fallback?: string) => string;
}

export const StudioTab: React.FC<StudioTabProps> = ({
  productFeeds,
  loadingFeeds,
  selectedFeedId,
  feedItems,
  loadingFeedItems,
  onOpenCreateFeedModal,
  onSelectFeed,
  onDeleteFeed,
  onOpenAddSkuModal,
  matrixProductName,
  setMatrixProductName,
  matrixCategory,
  setMatrixCategory,
  matrixTargetAudience,
  setMatrixTargetAudience,
  matrixResult,
  generatingMatrix,
  onGenerateCreativeMatrix,
  currentLang: _currentLang = 'ru',
  t: _t = (key: string, fallback?: string) => translateAdText(key, _currentLang, fallback),
}) => {
  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-6 rounded-xl border bg-gradient-to-r from-purple-500/10 via-pink-500/10 to-indigo-500/10 dark:from-purple-950/30 dark:via-pink-950/30 dark:to-indigo-950/30">
        <div className="flex items-center gap-4">
          <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl bg-purple-500/20 text-purple-600 dark:text-purple-400 font-extrabold text-2xl border border-purple-500/30">
            <Sparkles className="h-8 w-8 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xl font-bold">AI Multi-Format Creative Studio & DPA</h3>
              <Badge variant="outline" className="border-purple-500/40 bg-purple-500/10 text-purple-600 dark:text-purple-400">
                Phase 27
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              Генерируйте 5 взаимодополняющих рекламных форматов (текстовые карточки в чате, glassmorphic-виджеты, 9:16 Story-баннеры, Display лидерборды и сценарии для видео Reels/TikTok) и подключайте динамические каталоги товаров для автоматического таргетинга (Dynamic Product Ads).
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onOpenCreateFeedModal}
            className="border-purple-500/30 hover:bg-purple-500/10 text-purple-600 dark:text-purple-400"
          >
            <ShoppingBag className="mr-1.5 h-4 w-4" />
            Подключить Каталог (Feed)
          </Button>
        </div>
      </div>

      {/* 1. Multi-Format Repurposing Generator */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <Wand2 className="h-4 w-4 text-purple-500" />
                AI Мульти-Форматный Генератор Креативов
              </CardTitle>
              <CardDescription className="text-xs">
                Введите название и категорию продукта — нейросеть создаст полный комплект промо-материалов для всех каналов.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold text-foreground">Название продукта / Оффера</label>
              <Input
                placeholder="Например: MacBook Pro M3 Max"
                value={matrixProductName}
                onChange={(e) => setMatrixProductName(e.target.value)}
                className="mt-1 text-xs"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">Категория товаров</label>
              <Input
                placeholder="Например: Ноутбуки и Электроника"
                value={matrixCategory}
                onChange={(e) => setMatrixCategory(e.target.value)}
                className="mt-1 text-xs"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-foreground">Целевая аудитория (Промпт)</label>
              <Input
                placeholder="Например: Разработчики, дизайнеры и IT-специалисты"
                value={matrixTargetAudience}
                onChange={(e) => setMatrixTargetAudience(e.target.value)}
                className="mt-1 text-xs"
              />
            </div>
          </div>

          <div className="flex items-center justify-end">
            <Button
              size="sm"
              onClick={onGenerateCreativeMatrix}
              disabled={generatingMatrix}
              className="bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs"
            >
              {generatingMatrix ? (
                <RefreshCw className="mr-1.5 h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="mr-1.5 h-4 w-4" />
              )}
              {generatingMatrix ? 'Генерация 5 форматов...' : 'Сгенерировать 5-Форматный Пакет'}
            </Button>
          </div>

          {/* Matrix Results Showcase */}
          {matrixResult && (
            <div className="mt-6 space-y-6 pt-4 border-t">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-sm font-bold text-foreground flex items-center gap-2">
                    <span>Готовые рекламные материалы для: <strong>{matrixResult.product_name}</strong></span>
                    <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-600 text-xs">
                      {matrixResult.overall_health_score}% Creative Quality Score
                    </Badge>
                  </h4>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Категория: {matrixResult.category} • Аудитория: {matrixResult.target_audience}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Format 1: Native AI Chat Cards */}
                <Card className="border border-purple-500/20 bg-purple-50/30 dark:bg-purple-950/10">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-purple-600 dark:text-purple-400">
                        <Bot className="h-4 w-4" /> 1. Native Chat Text Card
                      </CardTitle>
                      <Badge variant="secondary" className="text-[10px]">AI Chat</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3 text-xs">
                    <div>
                      <div className="font-semibold text-foreground mb-1">Заголовки (3 угла):</div>
                      <ul className="space-y-1">
                        {(matrixResult.formats.text_card.headlines || []).map((h, i) => (
                          <li key={i} className="p-1.5 rounded bg-background border text-[11px] font-medium">
                            🔹 {h}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <div className="font-semibold text-foreground mb-1">Тексты описания:</div>
                      <ul className="space-y-1">
                        {(matrixResult.formats.text_card.descriptions || []).map((d, i) => (
                          <li key={i} className="p-1.5 rounded bg-background border text-[11px] text-muted-foreground">
                            {d}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(matrixResult.formats.text_card.badges || []).map((b, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300 text-[10px] font-semibold">
                          {b}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Format 2: Glassmorphic Interactive Widget */}
                <Card className="border border-blue-500/20 bg-blue-50/30 dark:bg-blue-950/10">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-blue-600 dark:text-blue-400">
                        <LayoutGrid className="h-4 w-4" /> 2. Rich Interactive Card
                      </CardTitle>
                      <Badge variant="secondary" className="text-[10px]">Interactive Widget</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="p-4 rounded-xl border bg-background/80 backdrop-blur-md shadow-sm space-y-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <span className="text-[10px] font-extrabold uppercase text-blue-600 tracking-wider">
                            {matrixResult.formats.rich_interactive_card.widget_title}
                          </span>
                          <h5 className="font-bold text-sm text-foreground mt-0.5">
                            {matrixResult.formats.rich_interactive_card.headline}
                          </h5>
                        </div>
                        <div className="flex items-center gap-1 text-amber-500 text-xs font-bold">
                          <span>★ {matrixResult.formats.rich_interactive_card.rating}</span>
                          <span className="text-muted-foreground text-[10px]">({matrixResult.formats.rich_interactive_card.reviews_count})</span>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-1 py-1">
                        {(matrixResult.formats.rich_interactive_card.features || []).map((f, i) => (
                          <div key={i} className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                            <CheckCircle className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                            <span>{f}</span>
                          </div>
                        ))}
                      </div>

                      <div className="flex items-center gap-2 pt-2 border-t">
                        <Button size="sm" className="w-full bg-blue-600 hover:bg-blue-700 text-white text-xs h-8">
                          {matrixResult.formats.rich_interactive_card.primary_cta}
                        </Button>
                        <Button size="sm" variant="outline" className="w-full text-xs h-8">
                          {matrixResult.formats.rich_interactive_card.secondary_cta}
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Format 3: 9:16 Vertical Story Banner */}
                <Card className="border border-pink-500/20 bg-pink-50/30 dark:bg-pink-950/10">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-pink-600 dark:text-pink-400">
                        <Smartphone className="h-4 w-4" /> 3. 9:16 Story Banner (Mobile)
                      </CardTitle>
                      <Badge variant="secondary" className="text-[10px]">1080 × 1920</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="max-w-[240px] mx-auto rounded-2xl overflow-hidden border-2 border-pink-500/30 shadow-lg relative bg-gradient-to-b from-purple-900 via-indigo-900 to-black text-white p-4 aspect-[9/16] flex flex-col justify-between">
                      <div className="flex justify-between items-start">
                        <span className="px-2 py-0.5 rounded-full bg-pink-500 text-white font-extrabold text-[10px] shadow-sm animate-pulse">
                          {matrixResult.formats.story_banner.sticker_badge}
                        </span>
                        <span className="text-[9px] opacity-70">Sponsored</span>
                      </div>

                      <div className="text-center space-y-1.5 my-auto">
                        <h4 className="font-extrabold text-base leading-tight text-white drop-shadow">
                          {matrixResult.formats.story_banner.title_overlay}
                        </h4>
                        <p className="text-[11px] text-pink-200 leading-snug">
                          {matrixResult.formats.story_banner.subtitle}
                        </p>
                      </div>

                      <div className="text-center space-y-1 pt-2">
                        <div className="flex justify-center text-pink-400 animate-bounce">
                          ▲
                        </div>
                        <div className="p-2 rounded-xl bg-white/20 backdrop-blur-md text-white font-bold text-xs uppercase tracking-wide">
                          {matrixResult.formats.story_banner.swipe_up_text}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Format 4: Display Leaderboard Banner */}
                <Card className="border border-emerald-500/20 bg-emerald-50/30 dark:bg-emerald-950/10">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                        <Monitor className="h-4 w-4" /> 4. Display Leaderboard & Banners
                      </CardTitle>
                      <Badge variant="secondary" className="text-[10px]">1200 × 628</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="p-4 rounded-xl border bg-gradient-to-r from-emerald-500/10 to-teal-500/10 flex flex-col justify-between gap-3">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold uppercase text-emerald-600 tracking-wider">
                          Display Ad 1200x628
                        </span>
                        <span className="text-[10px] text-muted-foreground">Swipies Ad Network</span>
                      </div>
                      <div>
                        <h5 className="font-extrabold text-sm text-foreground">
                          {matrixResult.formats.leaderboard_banner.banner_header}
                        </h5>
                        <p className="text-xs text-muted-foreground mt-1">
                          {matrixResult.formats.leaderboard_banner.banner_body}
                        </p>
                      </div>
                      <div className="flex justify-end">
                        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-7">
                          {matrixResult.formats.leaderboard_banner.button_text} →
                        </Button>
                      </div>
                    </div>

                    <div className="p-3 rounded-lg border bg-background flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-foreground">Поддерживаемые форматы: </span>
                        <span className="text-muted-foreground">{matrixResult.formats.leaderboard_banner.dimensions.join(' • ')}</span>
                      </div>
                      <Badge variant="outline" className="text-[10px]">SVG / HTML5 Ready</Badge>
                    </div>
                  </CardContent>
                </Card>

                {/* Format 5: Video Storyboard (Full width) */}
                <Card className="lg:col-span-2 border border-amber-500/20 bg-amber-50/30 dark:bg-amber-950/10">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
                        <Film className="h-4 w-4" /> 5. Video Storyboard Script (TikTok / Reels / Shorts - {matrixResult.formats.video_storyboard.duration_sec}s)
                      </CardTitle>
                      <Badge variant="secondary" className="text-[10px]">
                        {(matrixResult.formats.video_storyboard.target_platform || []).join(' • ')}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead>
                          <tr className="border-b bg-background/50">
                            <th className="py-2 px-3 font-semibold text-muted-foreground w-16">Сцена</th>
                            <th className="py-2 px-3 font-semibold text-muted-foreground w-24">Время</th>
                            <th className="py-2 px-3 font-semibold text-muted-foreground w-28">Фаза</th>
                            <th className="py-2 px-3 font-semibold text-muted-foreground">Визуальный ряд (Cues)</th>
                            <th className="py-2 px-3 font-semibold text-muted-foreground">Озвучка / Voiceover</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {(matrixResult.formats.video_storyboard.scenes || []).map((scene) => (
                            <tr key={scene.scene} className="hover:bg-background/80">
                              <td className="py-2.5 px-3 font-bold text-foreground">#{scene.scene}</td>
                              <td className="py-2.5 px-3 font-mono text-[11px] text-amber-600 font-semibold">{scene.timestamp}</td>
                              <td className="py-2.5 px-3">
                                <Badge
                                  variant="outline"
                                  className={
                                    scene.phase === 'Hook'
                                      ? 'border-rose-500/30 text-rose-600 text-[10px]'
                                      : scene.phase === 'CTA'
                                      ? 'border-emerald-500/30 text-emerald-600 text-[10px]'
                                      : 'border-blue-500/30 text-blue-600 text-[10px]'
                                  }
                                >
                                  {scene.phase}
                                </Badge>
                              </td>
                              <td className="py-2.5 px-3 text-[11px] text-foreground">{scene.visual}</td>
                              <td className="py-2.5 px-3 text-[11px] text-muted-foreground italic font-sans font-medium">
                                "{scene.voiceover}"
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2. Dynamic Product Ads (DPA) & Catalogs */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base flex items-center gap-2">
                <ShoppingBag className="h-4 w-4 text-emerald-500" />
                Dynamic Product Ads (DPA) & Каталоги Товаров
              </CardTitle>
              <CardDescription className="text-xs">
                Подключите фиды товаров для динамической подстановки SKU и цен в ответы AI-ассистента при товарных запросах.
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={onOpenCreateFeedModal}
                className="text-xs h-8"
              >
                <Plus className="mr-1 h-3.5 w-3.5" /> Создать Фид
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingFeeds ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : !Array.isArray(productFeeds) || productFeeds.length === 0 ? (
            <div className="p-8 text-center border-dashed border rounded-xl">
              <ShoppingBag className="h-10 w-10 text-muted-foreground mx-auto mb-2 opacity-50" />
              <h4 className="text-sm font-semibold text-foreground">У вас пока нет товарных каталогов</h4>
              <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto">
                Создайте фид вручную или укажите URL XML/JSON-каталога интернет-магазина для автоматического DPA-таргетинга.
              </p>
              <Button
                size="sm"
                onClick={onOpenCreateFeedModal}
                className="mt-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
              >
                <Plus className="mr-1.5 h-3.5 w-3.5" /> Создать первый фид
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Feed Selector Tabs / Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {(productFeeds || []).map((feed) => (
                  <div
                    key={feed.id}
                    onClick={() => onSelectFeed(feed.id)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      selectedFeedId === feed.id
                        ? 'border-emerald-500 bg-emerald-50/20 dark:bg-emerald-950/20 ring-1 ring-emerald-500'
                        : 'hover:border-zinc-400 bg-background'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-bold text-xs text-foreground truncate">{feed.name}</span>
                      <Badge
                        variant="outline"
                        className={
                          feed.sync_status === 'active'
                            ? 'border-emerald-500/30 text-emerald-600 text-[10px]'
                            : 'border-zinc-500/30 text-zinc-500 text-[10px]'
                        }
                      >
                        {feed.sync_status}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span>{feed.items_count} SKU товаров</span>
                      <span className="font-semibold text-foreground">{feed.currency}</span>
                    </div>
                    <div className="flex items-center justify-between pt-2 mt-2 border-t text-[10px] text-muted-foreground">
                      <span>Тип: {feed.feed_type}</span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteFeed(feed.id);
                        }}
                        className="text-red-500 hover:underline"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* SKU Items for Selected Feed */}
              {selectedFeedId && (
                <div className="pt-4 border-t space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold uppercase tracking-wider text-foreground">
                        Товары в каталоге ({(Array.isArray(feedItems) ? feedItems.length : 0)})
                      </h4>
                    </div>
                    <Button
                      size="sm"
                      onClick={onOpenAddSkuModal}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs h-7"
                    >
                      <Plus className="mr-1 h-3.5 w-3.5" /> Добавить Товар (SKU)
                    </Button>
                  </div>

                  {loadingFeedItems ? (
                    <div className="flex items-center justify-center py-8">
                      <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>
                  ) : !Array.isArray(feedItems) || feedItems.length === 0 ? (
                    <div className="p-6 text-center border-dashed border rounded-lg text-xs text-muted-foreground">
                      В выбранном каталоге пока нет товаров. Добавьте первый SKU вручную.
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {(feedItems || []).map((sku) => (
                        <div key={sku.id} className="p-3 rounded-lg border bg-background flex flex-col justify-between gap-2 shadow-sm">
                          <div>
                            <div className="flex items-start justify-between gap-2">
                              <span className="font-mono text-[10px] bg-muted px-1.5 py-0.5 rounded font-semibold text-muted-foreground">
                                {sku.sku}
                              </span>
                              {sku.discount_percent > 0 && (
                                <Badge variant="outline" className="border-red-500/30 bg-red-500/10 text-red-600 text-[10px] font-bold">
                                  -{sku.discount_percent}%
                                </Badge>
                              )}
                            </div>
                            <h5 className="font-bold text-xs text-foreground mt-1.5 line-clamp-1">{sku.title}</h5>
                            {sku.category && (
                              <p className="text-[10px] text-muted-foreground">{sku.category} {sku.brand && `• ${sku.brand}`}</p>
                            )}
                          </div>
                          <div className="flex items-center justify-between pt-2 border-t text-xs">
                            <div>
                              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                                ${toFixedSafe(sku.price, 2)}
                              </span>
                              {sku.original_price && (
                                <span className="text-[10px] text-muted-foreground line-through ml-1.5">
                                  ${toFixedSafe(sku.original_price, 2)}
                                </span>
                              )}
                            </div>
                            <Badge variant="secondary" className="text-[9px]">
                              {sku.availability}
                            </Badge>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
