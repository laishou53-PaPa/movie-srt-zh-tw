#!/usr/bin/env python3
"""Reusable SRT splitter, boundary analyzer, lossless merger, and TW subtitle QA tool."""

from __future__ import annotations

import argparse
import ctypes
import glob
import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_CHUNKS_DIR = "chunks"
DEFAULT_REPORT = "QA_Report.md"
CHUNK_SIZE = 60
CONTEXT_SIZE = 3

TIMECODE_RE = re.compile(
    r"^(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})(.*)$"
)
HTML_TAG_RE = re.compile(r"<[^>]+>")
ASCII_WORD_RE = re.compile(r"[A-Za-z]{2,}")
HALF_PERIOD_RE = re.compile(r"(?<!\d)\.(?!\d)")

# Unambiguous Mainland Chinese terms (regex patterns to avoid valid TW false positives like 演算法)
STRICT_MAINLAND_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (term, re.compile(re.escape(term)))
    for term in [
        "視頻", "軟件", "質量", "出租車", "土豆", "屏幕", "默認", "激光",
        "程序", "網絡", "服務器", "高清", "在線", "硬盤", "內存", "鼠標", "寬帶",
        "打印", "博客", "博主", "賬號", "賬戶", "登錄", "界面", "優盤", "反饋",
        "聖地亞哥", "斯坦福", "硅谷", "伯克利", "喬布斯", "奧巴馬", "特朗普", "比爾蓋茨",
        "數據庫", "人工智能", "互聯網", "計算機", "智能手機", "攝像頭",
        "公交車", "方便麵", "創可貼", "大巴", "搞定", "靠譜", "給力", "牛逼",
        "閨蜜", "顏值", "內卷", "正能量", "高大上", "接地氣", "刷屏", "拉黑",
        "素質", "概率", "硬件", "固件", "插件", "內核", "進程", "線程",
        "緩存", "字節", "代碼", "編程", "調試", "信息",
    ]
] + [("算法", re.compile(r"(?<!演)算法"))]

# Valid Taiwan characters that Windows LCMapStringEx maps to traditional variants
ALLOWED_TW_MAP_DIFF = {"台", "症", "岩"}

# Fallback strict Simplified-only characters for non-Windows platforms
FALLBACK_SIMPLIFIED_CHARS = set(
    "万与专业丛东丝丢两严丧个丰临为丽举么义乌乐乔习乡书买乱争亏亘亚产亩亲亵亿仅从仑仓仪们众会伛伞伟传伤伥伦伧伪伫佥侠侣侥侦侧侨侩侪侬俣俦俨俩俪俭债倾偬偻偾偿傥傧储傩"
    "兑兖兰关兴兹养兽冁内冈册写军农冯冲决况冻净凉减凑凛凤凫凭凯击凿刍刘则刚创删别刭刹刽刿剀剂剐剑剥剧劝办务劢动励劲劳势勋匀匦匮区医华协单卖卢卤卧卫却卺厅历厉压厌厍厕"
    "厢厣厦厨厩厮县参双发变叙叠叶号叹叽吓吕吗启吴呐呒呓呕呖呗员呙呛呜咏咙咛响哑哒哓哔哕哗哙哜哝哟唛唠唢唤啧啬啭啮啸喷喽喾嗫嗳嘘嘤嘱噜嚣团园囱围囵国图圆圹场块坚坛坜坝"
    "坞坟坠垄垆垒垦垧垩垫垭垲埘埙埚堑堕墒墙壮声壳壶处备够头夹夺奁奂奋奖奥妆妇妈妩妪妫姗娄娅娆娇娈娱娲娴婴婵婶媪嫒嫔嫱嬷孙学孪宝实宠审宪宫宽宾寝对寻导寿将尔尘尝尧尴尽"
    "层屉届属屡屦屿岁岂岖岗岘岚岛岽岿峄峡峤峥峦崂崃崭嵘嵛嵝巅巩巯币帅师帏帐帜带帧帮帱帻帼幂广庆庐庑库应庙庞废廪开弃弑张弥弪弯弹强归当录彦彻径徕忆忧忾态怂怃怄怅怆总怼"
    "怿恋恳恶恸恹恺恻恼恽悦悫悬悭悯惧惨惩惫惬惭惮惯愠愤愦慑懑懒戆戋戏戗战戬户执扩扪扫扬抚抛抟抠抡抢护报担拟拢拣拥拦拧拨择挚挛挝挞挟挠挡挢挣挤挥捞损捡换捣掳掴掷掸掺掼"
    "揽揿搀搁搂搅携摄摅摆摇摈摊撄撑撵撷撸撺擀擞攒敌敛数斋斓斩断无旧时旷昙昼显晋晓晔晕晖暂暧术杀杂权条来杨杩枞枢枣枥枨枪枫枭柠柽栀栅标栈栉栊栋栌栎栏树样栾桠桡桢档桤桥"
    "桦桧桨桩梦检棂椁椟椠椤椭楼榄榇榈榉槛槟槠横樯樱橱橹橼檩欢欤欧歼殁殇残殒殓殚殡殴毁毂毕毙毡毵氇氢氩氲汇汉汤汹沟没沣沤沥沦沧沩沪泪泶泷泸泺泻泼泽泾浃浅浆浇浈浊测浍济"
    "浏浑浒浓浔涛涝涞涟涠涡涣涤润涧涨涩渊渌渍渎渐渑渔渖渗温湾湿溃溅滗滚滞滠满滢滤滥滦滨滩潆潇潋潍潜澜濑濒灏灭灯灵灾灿炀炉炜炝点炼炽烁烂烃烛烟烦烧烨烩烫烬热焕焖焘爱爷"
    "牍牵牺犊状犷犹狈狞独狭狮狯狰狱狲猃猎猕猡猪猫献獭玑玛玮环现玺珏珐珑珲琏琐琼瑶瑷璎瓒瓯电画畅畲畴疖疗疟疠疡疮疯疱痈痉痨痪痫瘅瘗瘘瘪瘫瘾瘿癞癣癫皑皱皲盏盐监盖盗盘眦"
    "着睁睃睐睑瞒瞩矫矶矾矿砀码砖砗砚砺砻砾础硕硖硗硷碍碛碜碱礼祢祯祷祸禀禄禅秃秆积称秽税稣稳穑穷窃窍窑窜窝窥窦窭竖竞笃笋笔笕笺笼笾筚筛筝筹签简箦箧箨箩箪箫篑篓篮簖籁"
    "籴类籼粜粝粤粪粮糁紧絷纠纡红纣纤纥约级纨纩纪纫纬纭纯纰纱纲纳纵纶纷纸纹纺纽纾线绀绁绂练组绅细织终绉绊绋绌绍绎经绐绑绒结绕绗绘给绚绛络绝绞统绠绡绢绣绥绦继绨绩绪绫"
    "续绮绯绰绲绳维绵绶绷绸绺绻综绽绾绿缀缁缂缃缄缅缆缇缈缉缋缌缍缎缏缑缒缓缔缕编缗缘缙缚缛缜缝缟缠缡缢缣缤缥缦缧缨缩缪缫缬缭缮缯缰缱缲缳缴缵罂罗罚罢罴羁羟翘耧耸耻聂"
    "聋职聍联聩聪肃肠肤肾肿胀胁胆胧胪胫胶脉脍脏脐脑脓脔脚脱脶脸腻腼腽腾膑舆舣舰舱舻艰艳艹艺节芈芗芜芦苁苄苇苈苋苌苍苎苏茎茏茑茔茕荆荚荛荜荞荟荠荡荣荤荥荦荧荨荩荪荫荭"
    "药莅莱莲莳莴莶获莸莹莺萝萤营萦萧萨葱蒇蒉蒋蒌蓝蓟蓠蓣蓥蓦蔷蔹蔺蔼蕲蕴薮藓蘖虏虑虚虽虾虿蚀蚁蚂蚬蛊蛎蛏蛮蛰蛱蛲蛳蛴蜕蜗蝇蝈蝉蝼蝾衅衔补衬衮袄袅袜袭装裆裢裣裤褛褴见"
    "观规觅视觇览觉觊觋觌觎觏觐觑觞觯誉誊计订讣认讥讦讧讨让讪讫训议讯记讲讳讴讵讶讷许讹论讼讽设访诀证诂诃评诅识诈诉诊诋诌词诎诏译诒诓诔试诖诗诘诙诚诛诜话诞诟诠诡询诣"
    "诤该详诧诨诩诫诬语诮误诰诱诲诳说诵诶请诸诹诺读诼诽课诿谀谁谂调谄谅谆谇谈谊谋谌谍谎谏谐谑谒谓谔谕谖谗谘谙谚谛谜谝谟谠谡谢谣谤谥谦谧谨谩谪谬谭谮谯谰谱谲谳谴谵谶贝"
    "贞负贡财责贤败账货质贩贪贫贬购贮贯贰贱贲贳贴贵贶贷贸费贺贻贼贽贾贿赀赁赂赃资赅赆赇赈赉赊赋赌赎赏赐赓赔赕赖赘赙赚赛赜赝赞赠赡赢赣赵趋趱趸跃跄跞践跷跸跹跻踌踪踬踯"
    "蹑蹒蹰蹿躏躜躯车轧轨轩轫转轭轮软轰轲轳轴轵轶轸轹轺轻轼载轾轿辁辂较辄辅辆辇辈辉辊辋辍辎辏辐辑输辔辕辖辗辘辙辚辞辩辫边辽达迁过迈运还这进远违连迟迩迳迹选逊递逦逻遗"
    "遥邓邝邬邮邹邺邻郏郐郑郓郦郧郸酝酱酽酾酿释鉴銮錾钆钇针钉钊钋钌钍钎钏钐钒钓钔钕钗钙钛钜钝钞钟钠钡钢钣钤钥钦钧钨钩钪钫钬钭钮钯钰钱钲钳钴钵钶钸钹钺钻钼钽钾钿铀铁铂"
    "铃铄铅铆铈铉铊铋铌铍铎铐铑铒铕铖铗铙铛铜铝铟铠铡铢铣铤铥铧铨铩铪铫铬铭铮铯铰铱铲铳铴铵银铷铸铹铺铼铽链铿销锁锂锄锅锆锇锈锉锊锋锌锐锑锒锓锔锕锖锗错锚锛锞锟锡锢锣"
    "锤锥锦锩锬锭键锯锰锱锲锴锵锶锷锸锹锺锻锼锾镀镁镂镄镆镇镉镊镌镍镏镐镑镒镓镔镖镗镘镙镛镜镝镞镟镡镣镤镦镧镨镪镫镬镭镯镰镱镳镶长门闩闪闫闭问闯闰闱闲闳间闵闶闷闸闹闺"
    "闻闼闽闾阀阁阂阃阄阅阆阈阉阊阋阌阍阎阏阐阑阒阔阕阖阗阙阚队阳阴阵阶际陆陇陈陉陕陧陨险随隐隶隽难雏雠雳雾霁霭靓静靥鞑鞯韦韧韩韪韫韬韵页顶顷顸项顺须顼顽顾顿颀颁颂颃"
    "预颅领颇颈颉颊颌颍颏颐频颓颔颖颗题颚颛颜额颞颟颠颡颢颤颦颧风飑飒飓飕飘飙飞飨餍饥饧饨饩饪饫饬饭饮饯饰饱饲饴饵饶饷饺饼饽饿馁馄馅馆馈馊馋馍馏馐馑馒馔马驭驮驯驰驱驳"
    "驴驵驶驷驸驹驺驻驼驽驾驿骀骁骂骄骅骆骇骈骊骋验骏骐骑骒骓骖骗骘骚骛骜骝骞骟骠骡骢骣骤骥骧髅髋髌鬓魇魉鱼鱿鲁鲂鲈鲋鲍鲎鲐鲑鲒鲔鲕鲚鲛鲜鲟鲠鲡鲢鲣鲤鲥鲦鲧鲨鲩鲫鲭鲮"
    "鲰鲱鲲鲳鲵鲶鲷鲸鲻鲽鳃鳄鳅鳆鳇鳌鳍鳎鳏鳐鳓鳔鳕鳖鳗鳜鳝鳞鳟鳢鸟鸠鸡鸢鸣鸥鸦鸨鸩鸪鸫鸬鸭鸯鸱鸲鸳鸵鸶鸷鸸鸹鸺鸽鸾鸿鹁鹂鹃鹄鹅鹆鹇鹈鹉鹊鹌鹎鹏鹑鹕鹗鹘鹚鹜鹞鹣鹤鹦鹧"
    "鹨鹩鹪鹫鹬鹭鹰鹳鹾麦麸麽黄黉黩黪黾鼋鼍鼹齐齑齿龀龃龄龅龆龇龈龉龊龋龌龙龚龛龟"
)


def infer_output_name(input_path: Path) -> str:
    stem = input_path.stem
    for suffix in (".eng", ".en", "_eng", "_en"):
        if stem.lower().endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return f"{stem}_zh-TW.srt"


def resolve_input_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    candidates = [
        p
        for p in sorted(Path(".").glob("*.srt"))
        if not p.name.lower().endswith("_zh-tw.srt")
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise FileNotFoundError("No source .srt file found in workspace; pass --input.")
    raise ValueError(
        f"Multiple .srt files found ({[p.name for p in candidates]}); pass --input."
    )


def parse_timestamp_sec(ts: str) -> float:
    hms, ms = ts.split(",")
    h, m, s = map(int, hms.split(":"))
    return h * 3600.0 + m * 60.0 + s + int(ms) / 1000.0


def parse_srt(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    blocks = re.split(r"\n\s*\n", text)
    entries: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if len(lines) < 2:
            raise ValueError(f"Malformed SRT block #{idx}: {block!r}")
        raw_id = lines[0].strip()
        try:
            sub_id = int(raw_id)
        except ValueError as exc:
            raise ValueError(f"Invalid subtitle ID at block #{idx}: {raw_id!r}") from exc

        tc_line = lines[1].strip()
        m = TIMECODE_RE.match(tc_line)
        if not m:
            raise ValueError(f"Invalid timecode at ID {sub_id}: {tc_line!r}")

        start_ts, end_ts = m.group(1), m.group(2)
        duration = round(parse_timestamp_sec(end_ts) - parse_timestamp_sec(start_ts), 3)
        body = "\n".join(lines[2:])
        entries.append(
            {
                "id": sub_id,
                "timecode": tc_line,
                "duration": duration,
                "en": body,
            }
        )
    return entries


def check_timeline_sanity(entries: list[dict[str, Any]]) -> dict[str, Any]:
    non_positive_dur: list[dict[str, Any]] = []
    out_of_order: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    non_sequential_ids: list[dict[str, Any]] = []

    prev_end = -1.0
    prev_start = -1.0
    prev_id = 0

    for item in entries:
        sub_id = item["id"]
        m = TIMECODE_RE.match(item["timecode"])
        assert m is not None
        start_s = parse_timestamp_sec(m.group(1))
        end_s = parse_timestamp_sec(m.group(2))

        if prev_id != 0 and sub_id != prev_id + 1:
            non_sequential_ids.append({"prev_id": prev_id, "id": sub_id})

        if item["duration"] <= 0:
            non_positive_dur.append(
                {"id": sub_id, "timecode": item["timecode"], "duration": item["duration"]}
            )

        if start_s < prev_start:
            out_of_order.append({"id": sub_id, "timecode": item["timecode"]})
        elif start_s < prev_end:
            overlap_ms = round((prev_end - start_s) * 1000)
            overlaps.append(
                {
                    "prev_id": prev_id,
                    "id": sub_id,
                    "overlap_ms": overlap_ms,
                    "timecode": item["timecode"],
                }
            )

        prev_start = start_s
        prev_end = end_s
        prev_id = sub_id

    return {
        "total": len(entries),
        "start_id": entries[0]["id"] if entries else None,
        "end_id": entries[-1]["id"] if entries else None,
        "start_timecode": entries[0]["timecode"] if entries else None,
        "end_timecode": entries[-1]["timecode"] if entries else None,
        "non_sequential_ids": non_sequential_ids,
        "non_positive_dur": non_positive_dur,
        "out_of_order": out_of_order,
        "overlaps": overlaps,
    }


def cmd_split(args: argparse.Namespace) -> None:
    input_path = resolve_input_path(args.input)
    chunks_dir = Path(args.chunks_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input SRT not found: {input_path}")

    entries = parse_srt(input_path)
    if not entries:
        raise ValueError(f"No subtitles parsed from {input_path}")

    sanity = check_timeline_sanity(entries)
    chunks_dir.mkdir(parents=True, exist_ok=True)
    for old_file in chunks_dir.glob("chunk_*.json"):
        old_file.unlink()

    chunk_size = args.chunk_size
    context_size = args.context_size
    total_chunks = math.ceil(len(entries) / chunk_size)
    width = max(2, len(str(total_chunks)))

    for idx in range(total_chunks):
        start_i = idx * chunk_size
        end_i = min(start_i + chunk_size, len(entries))
        chunk_entries = entries[start_i:end_i]

        prev_ctx = [
            {
                "id": item["id"],
                "timecode": item["timecode"],
                "duration": item["duration"],
                "en": item["en"],
            }
            for item in entries[max(0, start_i - context_size) : start_i]
        ]
        next_ctx = [
            {
                "id": item["id"],
                "timecode": item["timecode"],
                "duration": item["duration"],
                "en": item["en"],
            }
            for item in entries[end_i : min(len(entries), end_i + context_size)]
        ]

        items = [
            {
                "id": item["id"],
                "timecode": item["timecode"],
                "duration": item["duration"],
                "en": item["en"],
                "zh": "",
            }
            for item in chunk_entries
        ]

        payload = {
            "chunk_index": idx + 1,
            "total_chunks": total_chunks,
            "source_file": input_path.name,
            "id_range": [items[0]["id"], items[-1]["id"]],
            "prev_context": prev_ctx,
            "items": items,
            "next_context": next_ctx,
        }

        chunk_name = f"chunk_{idx + 1:0{width}d}.json"
        (chunks_dir / chunk_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    html_cnt = sum(1 for e in entries if "<" in e["en"])
    sfx_cnt = sum(1 for e in entries if re.search(r"[\(\[].+?[\)\]]", e["en"]))
    spk_cnt = sum(
        1 for e in entries if re.search(r"(?:^|\n)-?\s*[A-Z][A-Z0-9 .'-]{1,25}:", e["en"])
    )
    short_cnt = sum(1 for e in entries if e["duration"] < 1.0)
    dual_cnt = sum(
        1 for e in entries if "\n-" in e["en"] or e["en"].startswith("-")
    )

    print(f"Split complete: {len(entries)} entries -> {total_chunks} chunks in '{chunks_dir}/'")
    print(f"Suggested output filename: {infer_output_name(input_path)}")
    print(f"ID range: {sanity['start_id']} .. {sanity['end_id']}")
    print(f"Time span: {sanity['start_timecode']} .. {sanity['end_timecode']}")
    print(
        "Source timeline sanity: "
        f"non_seq_ids={len(sanity['non_sequential_ids'])}, "
        f"non_pos_dur={len(sanity['non_positive_dur'])}, "
        f"out_of_order={len(sanity['out_of_order'])}, "
        f"overlaps={len(sanity['overlaps'])}"
    )
    print(
        f"Track profile: html={html_cnt}, sfx_parens={sfx_cnt}, "
        f"speaker_tags={spk_cnt}, dual_cues={dual_cnt}, short_lt_1s={short_cnt}"
    )


def load_chunks_sorted(chunks_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    files = list(chunks_dir.glob("chunk_*.json"))
    if not files:
        raise FileNotFoundError(f"No chunk_*.json files found in {chunks_dir}")

    def sort_key(p: Path) -> int:
        m = re.search(r"chunk_(\d+)\.json$", p.name)
        return int(m.group(1)) if m else 0

    files.sort(key=sort_key)
    return [(p.name, json.loads(p.read_text(encoding="utf-8-sig"))) for p in files]


def cmd_boundaries(args: argparse.Namespace) -> None:
    chunks = load_chunks_sorted(Path(args.chunks_dir))
    for i in range(len(chunks) - 1):
        fname_a, data_a = chunks[i]
        fname_b, data_b = chunks[i + 1]
        a = data_a["items"][-1]
        b = data_b["items"][0]
        end_a = parse_timestamp_sec(a["timecode"].split(" --> ")[1])
        start_b = parse_timestamp_sec(b["timecode"].split(" --> ")[0])
        gap = round(start_b - end_a, 2)
        t1 = a["en"].replace("\n", " ").strip()
        t2 = b["en"].replace("\n", " ").strip()
        status = "CLEAN" if t1.endswith((".", "?", "!", '"', "”", "♪")) else "mid  "
        print(
            f"{status} | {fname_a}->{fname_b} ({a['id']}->{b['id']}) "
            f"gap={gap:5.2f}s | {t1[-40:]} || {t2[:40]}"
        )


def clean_zh_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    return "\n".join(lines).strip("\n")


def cmd_merge(args: argparse.Namespace) -> None:
    input_path = resolve_input_path(args.input)
    output_path = Path(args.output) if args.output else Path(infer_output_name(input_path))
    chunks_dir = Path(args.chunks_dir)

    source_entries = parse_srt(input_path)
    chunks = load_chunks_sorted(chunks_dir)

    merged_items: list[tuple[str, dict[str, Any]]] = []
    for fname, data in chunks:
        for item in data.get("items", []):
            merged_items.append((fname, item))

    if len(merged_items) != len(source_entries):
        raise ValueError(
            f"Count mismatch during merge! Source has {len(source_entries)} entries, "
            f"chunks have {len(merged_items)} entries."
        )

    out_blocks: list[str] = []
    empty_count = 0
    for src, (fname, item) in zip(source_entries, merged_items):
        if item["id"] != src["id"]:
            raise ValueError(
                f"ID mismatch in {fname}: expected {src['id']}, got {item['id']}"
            )
        if item["timecode"] != src["timecode"]:
            raise ValueError(
                f"Timecode mismatch in {fname} ID {src['id']}: "
                f"expected {src['timecode']!r}, got {item['timecode']!r}"
            )
        zh = clean_zh_text(item.get("zh", ""))
        if not zh.strip():
            empty_count += 1
        out_blocks.append(f"{src['id']}\n{src['timecode']}\n{zh}")

    output_path.write_text("\n\n".join(out_blocks) + "\n", encoding="utf-8", newline="\n")
    print(f"Merge complete: {len(out_blocks)} entries -> '{output_path}' (UTF-8)")
    if empty_count:
        print(f"Warning: {empty_count} entries currently have empty 'zh'.")


def fullwidth_length(line: str) -> float:
    total = 0.0
    for ch in line:
        if ch == "\u3000" or ch in ("…", "—") or ord(ch) > 127:
            total += 1.0
        elif unicodedata.east_asian_width(ch) in ("W", "F"):
            total += 1.0
        else:
            total += 0.5
    return total


def cps_char_count(zh: str) -> int:
    cleaned = [
        line[2:] if line.startswith("- ") else line for line in zh.split("\n")
    ]
    return sum(1 for c in "".join(cleaned) if not c.isspace())


def to_traditional_win32(text: str) -> str:
    kernel32 = ctypes.windll.kernel32
    LCMAP_TRADITIONAL_CHINESE = 0x04000000
    buf_len = len(text) * 2 + 16
    buf = ctypes.create_unicode_buffer(buf_len)
    res = kernel32.LCMapStringEx(
        "zh-TW", LCMAP_TRADITIONAL_CHINESE, text, -1, buf, buf_len, None, None, 0
    )
    return buf.value if res != 0 else text


def detect_simplified_chars(text: str) -> list[tuple[str, str]]:
    if sys.platform == "win32":
        trad = to_traditional_win32(text)
        return [
            (o, t)
            for o, t in zip(text, trad)
            if o != t and o not in ALLOWED_TW_MAP_DIFF
        ]
    return [(c, "?") for c in text if c in FALLBACK_SIMPLIFIED_CHARS]


def parse_zh_srt(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text:
        return []
    blocks = re.split(r"\n{2,}", text)
    entries: list[dict[str, Any]] = []
    for idx, block in enumerate(blocks, start=1):
        lines = block.split("\n")
        if len(lines) < 2:
            raise ValueError(f"Malformed translated SRT block #{idx}: {block!r}")
        entries.append(
            {
                "id": int(lines[0].strip()),
                "timecode": lines[1].strip(),
                "zh": "\n".join(lines[2:]),
            }
        )
    return entries


def cmd_qa(args: argparse.Namespace) -> None:
    input_path = resolve_input_path(args.input)
    output_path = Path(args.output) if args.output else Path(infer_output_name(input_path))
    chunks_dir = Path(args.chunks_dir)
    report_path = Path(args.report)

    en_entries = parse_srt(input_path)
    zh_entries = parse_zh_srt(output_path)

    id_to_chunk: dict[int, str] = {}
    if chunks_dir.exists():
        for fname, data in load_chunks_sorted(chunks_dir):
            for item in data.get("items", []):
                id_to_chunk[item["id"]] = fname

    def chunk_of(sub_id: int, idx: int) -> str:
        return id_to_chunk.get(sub_id, f"chunk_{(idx // CHUNK_SIZE) + 1:02d}.json")

    en_sanity = check_timeline_sanity(en_entries)
    count_match = len(en_entries) == len(zh_entries)
    start_id_match = (
        en_entries[0]["id"] == zh_entries[0]["id"] if en_entries and zh_entries else False
    )
    end_id_match = (
        en_entries[-1]["id"] == zh_entries[-1]["id"] if en_entries and zh_entries else False
    )

    timecode_mismatches: list[dict[str, Any]] = []
    if count_match:
        for i, (e, z) in enumerate(zip(en_entries, zh_entries)):
            if e["id"] != z["id"] or e["timecode"] != z["timecode"]:
                timecode_mismatches.append(
                    {
                        "chunk": chunk_of(e["id"], i),
                        "id": e["id"],
                        "zh_id": z["id"],
                        "en_tc": e["timecode"],
                        "zh_tc": z["timecode"],
                    }
                )

    empty_zh: list[dict[str, Any]] = []
    residual_en: list[dict[str, Any]] = []
    residual_html: list[dict[str, Any]] = []
    over_2_lines: list[dict[str, Any]] = []
    line_over_18: list[dict[str, Any]] = []
    line_17_18: list[dict[str, Any]] = []
    high_cps_normal: list[dict[str, Any]] = []
    high_cps_short: list[dict[str, Any]] = []
    forbidden_punct: list[dict[str, Any]] = []
    inline_dual: list[dict[str, Any]] = []
    simplified_issues: list[dict[str, Any]] = []
    mainland_term_issues: list[dict[str, Any]] = []
    ni_count = {"你": 0, "妳": 0, "您": 0}

    pair_iter = zip(en_entries, zh_entries) if count_match else []
    for i, (e, z) in enumerate(pair_iter):
        sub_id = e["id"]
        cname = chunk_of(sub_id, i)
        dur = e["duration"]
        zh = z["zh"].strip("\n")

        if not zh.strip():
            empty_zh.append({"chunk": cname, "id": sub_id, "en": e["en"]})
            continue

        for p in ni_count:
            ni_count[p] += zh.count(p)

        if HTML_TAG_RE.search(zh):
            residual_html.append({"chunk": cname, "id": sub_id, "zh": zh})

        ascii_matches = ASCII_WORD_RE.findall(zh)
        if ascii_matches:
            residual_en.append(
                {"chunk": cname, "id": sub_id, "words": ascii_matches, "zh": zh}
            )

        lines = zh.split("\n")
        if len(lines) > 2:
            over_2_lines.append({"chunk": cname, "id": sub_id, "lines": len(lines), "zh": zh})

        for li, line in enumerate(lines, start=1):
            fw = fullwidth_length(line)
            if math.ceil(fw) > 18:
                line_over_18.append(
                    {"chunk": cname, "id": sub_id, "line_no": li, "fw": fw, "line": line}
                )
            elif math.ceil(fw) > 16:
                line_17_18.append(
                    {"chunk": cname, "id": sub_id, "line_no": li, "fw": fw, "line": line}
                )
            if re.search(r"\S\s+-\s*\S", line):
                inline_dual.append({"chunk": cname, "id": sub_id, "line": line})

        chars = cps_char_count(zh)
        cps = round(chars / dur, 2) if dur > 0 else 999.0
        if cps > 13.0:
            rec = {"chunk": cname, "id": sub_id, "dur": dur, "chars": chars, "cps": cps, "zh": zh}
            if dur >= 1.0:
                high_cps_normal.append(rec)
            else:
                high_cps_short.append(rec)

        punct_hits = []
        if "\u3000" in zh:
            punct_hits.append("全形空格(　)")
        if "," in zh:
            punct_hits.append("半形逗號(,)")
        if HALF_PERIOD_RE.search(zh):
            punct_hits.append("半形句號(.)")
        if ".." in zh:
            punct_hits.append("半形刪節號(..)")
        if "--" in zh:
            punct_hits.append("半形破折號(--)")
        if any(m.group(0) != "……" for m in re.finditer(r"…+", zh)):
            punct_hits.append("刪節號非兩格")
        if any(m.group(0) != "——" for m in re.finditer(r"—+", zh)):
            punct_hits.append("破折號非兩格")
        for line in lines:
            body = line[2:] if line.startswith("- ") else line
            if re.search(r"[\u4e00-\u9fff] [\u4e00-\u9fff]", body):
                punct_hits.append("中文字間多餘空格")
            if re.search(
                r"[\u4e00-\u9fff「」『』《》（）【】？！，。、：；] +[A-Za-z0-9%]"
                r"|[A-Za-z0-9%] +[\u4e00-\u9fff「」『』《》（）【】？！，。、：；]",
                body,
            ):
                punct_hits.append("中英數字間多餘空格")
            if not (body.startswith("♪ ") and body.endswith(" ♪")):
                if re.search(r"[？！……——，。、：「」] | [？！……——，。、：「」]", body):
                    punct_hits.append("中文標點旁多餘空格")
        punct_hits = list(dict.fromkeys(punct_hits))
        if punct_hits:
            forbidden_punct.append(
                {"chunk": cname, "id": sub_id, "hits": punct_hits, "zh": zh}
            )

        simp = detect_simplified_chars(zh)
        if simp:
            simplified_issues.append(
                {"chunk": cname, "id": sub_id, "diffs": simp, "zh": zh}
            )

        term_hits = [term for term, pat in STRICT_MAINLAND_PATTERNS if pat.search(zh)]
        if term_hits:
            mainland_term_issues.append(
                {"chunk": cname, "id": sub_id, "terms": term_hits, "zh": zh}
            )

    critical_count = (
        (0 if count_match else 1)
        + (0 if start_id_match and end_id_match else 1)
        + len(timecode_mismatches)
        + len(empty_zh)
        + len(residual_html)
        + len(over_2_lines)
        + len(line_over_18)
        + len(inline_dual)
        + len(forbidden_punct)
        + len(simplified_issues)
        + len(mainland_term_issues)
    )

    lines_md: list[str] = [
        "# QA Report - 台灣繁體中文字幕自動化品管報告",
        "",
        f"- **原始英文字幕**：`{input_path.name}`",
        f"- **繁中輸出字幕**：`{output_path.name}`",
        f"- **總體狀態**：{'✅ PASS（必改項目全數通過）' if critical_count == 0 else f'❌ FAIL（共有 {critical_count} 項必改異常）'}",
        "",
        "## 1. 時間軸與結構完整性檢查（Timeline & Sync Verification）",
        "",
        f"- **總條數一致**：{'✅' if count_match else '❌'} 英文 `{len(en_entries)}` 條 / 中文 `{len(zh_entries)}` 條",
        f"- **起始 / 結束 ID 一致**：{'✅' if (start_id_match and end_id_match) else '❌'} "
        f"英文 `{en_sanity['start_id']}~{en_sanity['end_id']}` / 中文 `{zh_entries[0]['id'] if zh_entries else None}~{zh_entries[-1]['id'] if zh_entries else None}`",
        f"- **全片時間軸 100% 逐條比對**：{'✅ 零誤差' if not timecode_mismatches else f'❌ {len(timecode_mismatches)} 條不一致'}",
        f"- **電影片長與時間跨度**：`{en_sanity['start_timecode']}` 至 `{en_sanity['end_timecode']}`",
        f"- **原始時間軸播放健康度**：非連續 ID `{len(en_sanity['non_sequential_ids'])}`｜零/負時長 `{len(en_sanity['non_positive_dur'])}`｜倒流 `{len(en_sanity['out_of_order'])}`｜重疊 `{len(en_sanity['overlaps'])}`",
        f"- **第二人稱代詞統計**：`你` {ni_count['你']} 次｜`妳` {ni_count['妳']} 次｜`您` {ni_count['您']} 次",
        "",
        "## 2. 異常統計總覽",
        "",
        "| 檢查項目 | 嚴重度 | 異常筆數 |",
        "| :--- | :--- | ---: |",
        f"| 時間戳記不一致 | 必改 | {len(timecode_mismatches)} |",
        f"| 漏翻（空白譯文） | 必改 | {len(empty_zh)} |",
        f"| 殘留 HTML 標籤 | 必改 | {len(residual_html)} |",
        f"| 單條超過 2 行 | 必改 | {len(over_2_lines)} |",
        f"| 單行超過 18 全形字 | 必改 | {len(line_over_18)} |",
        f"| 雙人對話未換行（`- A - B`） | 必改 | {len(inline_dual)} |",
        f"| 不當空格／半形標點（　、中英數空格、,.） | 必改 | {len(forbidden_punct)} |",
        f"| 簡體字殘留 | 必改 | {len(simplified_issues)} |",
        f"| 大陸用語殘留 | 必改 | {len(mainland_term_issues)} |",
        f"| 單行 17～18 全形字 | 警告 | {len(line_17_18)} |",
        f"| 殘留英文單字/縮寫 | 檢視 | {len(residual_en)} |",
        f"| CPS > 13 字/秒（一般 ≥1.0s） | 警告 | {len(high_cps_normal)} |",
        f"| CPS > 13 字/秒（極短 <1.0s） | 提示 | {len(high_cps_short)} |",
        "",
    ]

    def add_section(title: str, items: list[str]) -> None:
        lines_md.append(f"## {title}")
        lines_md.append("")
        if not items:
            lines_md.append("- 無異常")
        else:
            lines_md.extend(items[:200])
            if len(items) > 200:
                lines_md.append(f"- （其餘 {len(items) - 200} 筆略）")
        lines_md.append("")

    add_section(
        "3. 時間軸不一致與異常明細",
        [
            f"- `{m['chunk']}` ID `{m['id']}`：EN `{m['en_tc']}` vs ZH `{m['zh_tc']}`"
            for m in timecode_mismatches
        ]
        + [
            f"- [原始時間軸重疊] ID `{o['prev_id']}` -> `{o['id']}` 重疊 `{o['overlap_ms']}ms`"
            for o in en_sanity["overlaps"]
        ],
    )
    add_section(
        "4. 漏翻與殘留 HTML／英文明細",
        [f"- [漏翻] `{x['chunk']}` ID `{x['id']}`：`{x['en']}`" for x in empty_zh]
        + [f"- [HTML] `{x['chunk']}` ID `{x['id']}`：`{x['zh']}`" for x in residual_html]
        + [
            f"- [殘留英文] `{x['chunk']}` ID `{x['id']}` ({', '.join(x['words'])})：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in residual_en
        ],
    )
    add_section(
        "5. 行數、字數超標與雙人對話格式明細",
        [
            f"- [超過2行-必改] `{x['chunk']}` ID `{x['id']}` ({x['lines']} 行)：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in over_2_lines
        ]
        + [
            f"- [>18全形字-必改] `{x['chunk']}` ID `{x['id']}` 第{x['line_no']}行 ({x['fw']}字)：`{x['line']}`"
            for x in line_over_18
        ]
        + [
            f"- [雙人對話未換行-必改] `{x['chunk']}` ID `{x['id']}`：`{x['line']}`"
            for x in inline_dual
        ]
        + [
            f"- [17~18全形字-警告] `{x['chunk']}` ID `{x['id']}` 第{x['line_no']}行 ({x['fw']}字)：`{x['line']}`"
            for x in line_17_18
        ],
    )
    add_section(
        "6. 不當空格／半形標點、簡體字與大陸用語明細",
        [
            f"- [標點／空格-必改] `{x['chunk']}` ID `{x['id']}` ({', '.join(x['hits'])})：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in forbidden_punct
        ]
        + [
            f"- [簡體字-必改] `{x['chunk']}` ID `{x['id']}` ({x['diffs']})：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in simplified_issues
        ]
        + [
            f"- [大陸用語-必改] `{x['chunk']}` ID `{x['id']}` ({', '.join(x['terms'])})：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in mainland_term_issues
        ],
    )
    add_section(
        "7. 閱讀速度 CPS > 13 字/秒明細",
        [
            f"- [過密-一般 ≥1.0s] `{x['chunk']}` ID `{x['id']}` ({x['chars']}字 / {x['dur']}s = {x['cps']} CPS)：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in high_cps_normal
        ]
        + [
            f"- [過密-極短 <1.0s] `{x['chunk']}` ID `{x['id']}` ({x['chars']}字 / {x['dur']}s = {x['cps']} CPS)：`{x['zh'].replace(chr(10), ' / ')}`"
            for x in high_cps_short
        ],
    )

    report_path.write_text("\n".join(lines_md), encoding="utf-8", newline="\n")
    print(
        f"QA complete -> '{report_path}': critical={critical_count}, "
        f"warn_17_18={len(line_17_18)}, cps_normal={len(high_cps_normal)}, "
        f"cps_short={len(high_cps_short)}, residual_en={len(residual_en)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Movie SRT Split / Boundaries / Merge / QA")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("split", "boundaries", "merge", "qa"):
        p = sub.add_parser(name)
        p.add_argument("--input", default=None, help="Source English .srt file")
        p.add_argument("--output", default=None, help="Output zh-TW .srt file")
        p.add_argument("--chunks-dir", default=DEFAULT_CHUNKS_DIR)
        p.add_argument("--report", default=DEFAULT_REPORT)
        if name == "split":
            p.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
            p.add_argument("--context-size", type=int, default=CONTEXT_SIZE)

    args = parser.parse_args()
    if args.command == "split":
        cmd_split(args)
    elif args.command == "boundaries":
        cmd_boundaries(args)
    elif args.command == "merge":
        cmd_merge(args)
    elif args.command == "qa":
        cmd_qa(args)


if __name__ == "__main__":
    main()
