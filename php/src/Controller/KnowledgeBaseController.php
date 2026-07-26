<?php
declare(strict_types=1);

class KnowledgeBaseController
{
    private const WIKI_DIR = __DIR__ . '/../../../../docs/wiki';

    public function index(): array
    {
        $files = glob(self::WIKI_DIR . '/*.md');
        $articles = [];
        foreach ($files as $file) {
            $slug = basename($file, '.md');
            $content = file_get_contents($file);
            $title = $this->extractTitle($content) ?: ucwords(str_replace(['_', '-'], ' ', $slug));
            $category = $this->extractCategory($content) ?: 'General';
            $articles[] = [
                'slug' => $slug,
                'title' => $title,
                'category' => $category,
            ];
        }
        usort($articles, fn($a, $b) => strcmp($a['category'], $b['category']) ?: strcmp($a['title'], $b['title']));
        return ['articles' => $articles];
    }

    public function article(string $slug): ?array
    {
        $file = self::WIKI_DIR . '/' . $slug . '.md';
        if (!is_file($file)) {
            return null;
        }
        $content = file_get_contents($file);
        return [
            'slug' => $slug,
            'title' => $this->extractTitle($content) ?: ucwords(str_replace(['_', '-'], ' ', $slug)),
            'category' => $this->extractCategory($content) ?: 'General',
            'body' => $this->mdToHtml($content),
        ];
    }

    private function extractTitle(string $md): ?string
    {
        if (preg_match('/^#\s+(.+)$/m', $md, $m)) {
            return trim($m[1]);
        }
        return null;
    }

    private function extractCategory(string $md): ?string
    {
        if (preg_match('/\[\[Category:\s*([^\]]+)\]\]/', $md, $m)) {
            return trim($m[1]);
        }
        return null;
    }

    private function mdToHtml(string $md): string
    {
        $md = preg_replace('/\[\[Category:[^\]]+\]\]/', '', $md);
        $html = htmlspecialchars($md, ENT_QUOTES | ENT_HTML5);
        $html = preg_replace('/^#{1,6}\s+(.+)$/m', '<h3>$1</h3>', $html);
        $html = preg_replace('/^\*\s+(.+)$/m', '<li>$1</li>', $html);
        $html = preg_replace('/(<li>.*<\/li>\n?)+/s', '<ul>$0</ul>', $html);
        $html = preg_replace('/^> \s*(.+)$/m', '<blockquote>$1</blockquote>', $html);
        $html = preg_replace('/`([^`]+)`/', '<code>$1</code>', $html);
        $html = preg_replace('/\[([^\]]+)\]\(([^)]+)\)/', '<a href="$2" target="_blank">$1</a>', $html);
        $html = nl2br($html);
        return $html;
    }
}
