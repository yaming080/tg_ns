"""Two-call compatibility check, never connects to Telegram."""
import base64
import io
import json
from pathlib import Path
from openai import OpenAI
from PIL import Image
from news_review_cache import request_text, review_session


def main():
    client=OpenAI(max_retries=0,timeout=90)
    # Respect this bot's existing monthly spending when testing the new route.
    state=json.loads(Path('news_state.json').read_text(encoding='utf8'))
    stream=io.BytesIO();Image.new('RGB',(256,256),(255,0,0)).save(stream,format='PNG')
    payload=[{'role':'user','content':[
        {'type':'input_text','text':'Return JSON only: {"color":"red" or "blue"}. Identify the image color.'},
        {'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode(),'detail':'high'}]}]
    def save():
        # Public CI artifact contains aggregate usage only, never article/cache text.
        Path('model-validation-usage.json').write_text(json.dumps({
            'model_check':'Luna image and Sol source review; no Telegram',
            'latest_run':state['ai_review'].get('recent_runs',[])[-1:]
        },ensure_ascii=False,indent=2),encoding='utf8')
    with review_session(state,save) as store:
        text=request_text(client,'gpt-6-luna',payload,stage='image_review')
        assert json.loads(text)=={'color':'red'},'Luna vision/JSON check failed'
        verdict=request_text(client,'gpt-6-luna',
            'Return JSON only. Source: Example Bank plans a pilot in December; it has not launched yet. '
            'Summary: Example Bank launched its service today. '
            'Return {"publish":false,"reason":"the source describes a plan, not an actual launch"}.',
            stage='source_review')
        assert json.loads(verdict)['publish'] is False,'Sol factual-check contract failed'
        print('LUNA_IMAGE_JSON_AND_SOL_SOURCE_ROUTE_OK; NO_TELEGRAM_SEND')
    print('Compatibility check USD:',round(store.estimated_usd,9))


if __name__=='__main__':main()
