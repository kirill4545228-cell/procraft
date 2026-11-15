package io.github.artcraftandroid.procraft.i18n

import android.content.Context
import android.util.Log
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/**
 * The app's name, and the language of its interface text.
 *
 * The English text in the code is the key. `assets/i18n/ru.tsv` holds one `English<TAB>Russian` pair
 * per line. A `{}` in the key stands for a number or name filled in at run time (it matches any
 * text); in the translation `{}` (in order) or `{1}`, `{2}` (by position) put the pieces back.
 * Anything without an entry is shown as it is, in English. [toggle] switches the language; text
 * that went through [tr] in a composable redraws by itself.
 */
object I18n {
    /** The name the app goes by; "ProCraft" anywhere in the text is shown as this. */
    const val BRAND = "Procreate Android"
    private const val ORIGINAL = "ProCraft"

    private const val TAG = "ProCraftI18n"
    private const val PREFS = "i18n"
    private const val KEY = "language"

    @Volatile private var loaded = false
    private var exact: Map<String, String> = emptyMap()
    private var patterns: List<Pair<Regex, String>> = emptyList()
    private val cache = ConcurrentHashMap<String, String>()
    private val missed = ConcurrentHashMap.newKeySet<String>()

    private var russian by mutableStateOf(false)

    /** Whether the interface is in Russian now. */
    val isRussian: Boolean get() = russian

    /** Loads the dictionary and the chosen language (the phone's, until one is chosen). Safe to call again. */
    @Synchronized
    fun init(context: Context) {
        if (loaded) return
        val app = context.applicationContext
        val saved = runCatching { app.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null) }.getOrNull()
        russian = when (saved) {
            "ru" -> true
            "en" -> false
            else -> Locale.getDefault().language == "ru"
        }
        val ex = HashMap<String, String>()
        val pat = ArrayList<Pair<Regex, String>>()
        runCatching {
            app.assets.open("i18n/ru.tsv").bufferedReader(Charsets.UTF_8).useLines { lines ->
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
        loaded = true
    }

    /** Switches the interface to Russian or back to English, and remembers it. */
    fun setRussian(context: Context, on: Boolean) {
        init(context)
        runCatching {
            context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putString(KEY, if (on) "ru" else "en").apply()
        }
        cache.clear()
        russian = on
    }

    fun toggle(context: Context) = setRussian(context, !russian)

    /** [s] in the chosen language, with the app's name in it. */
    fun tr(s: String): String {
        // read here, so what shows it redraws when the language changes
        val ru = russian
        val text = if (ru && loaded) translated(s) else s
        return if (text.contains(ORIGINAL)) text.replace(ORIGINAL, BRAND) else text
    }

    private fun translated(s: String): String {
        if (s.isEmpty() || (exact.isEmpty() && patterns.isEmpty())) return s
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
            for (n in 1 until groups.size) out = out.replace("{$n}", translated(groups[n]))
            while (out.contains("{}") && i + 1 < groups.size) {
                i++
                out = out.replaceFirst("{}", translated(groups[i]))
            }
            return out
        }
        return s
    }
}
