package io.github.artcraftandroid.procraft.i18n

import android.content.Context
import android.util.Log
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * Runtime translation of the interface text.
 *
 * The English text in the code is the key. `assets/i18n/<lang>.tsv` holds one `English<TAB>Translation`
 * pair per line. A `{}` in the key stands for a number or name filled in at run time (it matches any
 * text); in the translation `{}` (in order) or `{1}`, `{2}` (by position) put the pieces back.
 * Anything without an entry is shown as it is, in English.
 */
object I18n {
    private const val TAG = "ProCraftI18n"

    @Volatile private var ready = false
    private var exact: Map<String, String> = emptyMap()
    private var patterns: List<Pair<Regex, String>> = emptyList()
    private val cache = ConcurrentHashMap<String, String>()
    private val missed = ConcurrentHashMap.newKeySet<String>()

    /** Loads the dictionary for the phone's language (Russian only for now). Safe to call again. */
    @Synchronized
    fun init(context: Context) {
        if (ready) return
        val lang = Locale.getDefault().language
        if (lang != "ru") {
            ready = true
            return
        }
        val ex = HashMap<String, String>()
        val pat = ArrayList<Pair<Regex, String>>()
        runCatching {
            context.applicationContext.assets.open("i18n/ru.tsv").bufferedReader(Charsets.UTF_8).useLines { lines ->
                for (raw in lines) {
                    if (raw.isEmpty() || raw.startsWith("#")) continue
                    val tab = raw.indexOf('\t')
                    if (tab <= 0) continue
                    val key = raw.substring(0, tab).replace("\\n", "\n")
                    val value = raw.substring(tab + 1).replace("\\n", "\n")
                    if (key.contains("{}")) {
                        val parts = key.split("{}").joinToString("(.+?)") { Regex.escape(it) }
                        pat.add(Regex("^$parts$", RegexOption.DOT_MATCHES_ALL) to value)
                    } else {
                        ex[key] = value
                    }
                }
            }
        }.onFailure { Log.w(TAG, "ru.tsv failed to load", it) }
        // the most specific patterns (most fixed text) first
        pat.sortByDescending { it.first.pattern.length }
        exact = ex
        patterns = pat
        ready = true
    }

    /** The translation of [s], or [s] itself when there is none. */
    fun tr(s: String): String {
        if (!ready || s.isEmpty() || (exact.isEmpty() && patterns.isEmpty())) return s
        cache[s]?.let { return it }
        val out = translate(s)
        if (cache.size < 8000) cache[s] = out
        if (out === s && s.any { it in 'A'..'Z' || it in 'a'..'z' } && missed.add(s)) {
            Log.d(TAG, "MISS\t" + s.replace("\n", "\\n"))
        }
        return out
    }

    private fun translate(s: String): String {
        exact[s]?.let { return it }
        for ((re, value) in patterns) {
            val m = re.matchEntire(s) ?: continue
            val groups = m.groupValues
            var i = 0
            var out = value
            // numbered pieces first, then the plain ones in order
            for (n in 1 until groups.size) out = out.replace("{$n}", tr(groups[n]))
            while (out.contains("{}") && i + 1 < groups.size) {
                i++
                out = out.replaceFirst("{}", tr(groups[i]))
            }
            return out
        }
        return s
    }
}
