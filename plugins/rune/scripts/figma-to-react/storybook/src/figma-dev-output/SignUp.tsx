import React from "react";

export default function SignUp() {
  return (
    <div className="w-[1440px] h-[1737px] relative bg-white overflow-hidden">
      <div className="left-[412px] top-[80px] absolute inline-flex flex-col justify-center items-center gap-12">
        <div className="flex flex-col justify-start items-center gap-2">
          <div className="w-12 h-12 bg-stone-300 rounded-full" />
          <div className="text-center justify-center text-zinc-800 text-3xl font-medium font-['Poppins']">
            Sign up for free to start live-streaming
          </div>
        </div>
        <div className="flex flex-col justify-start items-start gap-4">
          <div
            data-property-1="FB"
            className="w-[578px] h-16 relative bg-white rounded-[32px] outline outline-1 outline-offset-[-1px] outline-zinc-800 overflow-hidden"
          >
            <div className="left-[141.50px] top-[16px] absolute inline-flex justify-center items-center gap-4">
              <div data-property-1="Facebook" className="w-8 h-8 relative">
                <div className="w-7 h-7 left-[2px] top-[2px] absolute bg-sky-500 rounded-full" />
                <div className="w-3 h-5 left-[10px] top-[8px] absolute bg-white" />
              </div>
              <div className="justify-center text-zinc-800 text-2xl font-normal font-['Avenir']">
                Sign up with Facebook
              </div>
            </div>
          </div>
          <div
            data-property-1="Google"
            className="w-[578px] h-16 relative bg-white rounded-[32px] outline outline-1 outline-offset-[-1px] outline-zinc-800 overflow-hidden"
          >
            <div className="left-[158.50px] top-[15px] absolute inline-flex justify-center items-center gap-4">
              <div
                data-property-1="google"
                className="w-6 h-6 relative overflow-hidden"
              >
                <div className="w-2.5 h-2.5 left-[12.22px] top-[10.09px] absolute bg-blue-500" />
                <div className="w-4 h-2 left-[2.64px] top-[14.08px] absolute bg-green-600" />
                <div className="w-1 h-2.5 left-[1.50px] top-[7.24px] absolute bg-yellow-500" />
                <div className="w-4 h-2 left-[2.64px] top-[1.50px] absolute bg-red-500" />
              </div>
              <div className="justify-center text-zinc-800 text-2xl font-normal font-['Avenir']">
                Sign up with Google
              </div>
            </div>
          </div>
          <div
            data-property-1="Twitter"
            className="w-[578px] h-16 relative bg-white rounded-[32px] outline outline-1 outline-offset-[-1px] outline-zinc-800 overflow-hidden"
          >
            <div className="left-[158.50px] top-[15px] absolute inline-flex justify-center items-center gap-4">
              <div data-property-1="twitter" className="w-8 h-8 relative">
                <div className="w-7 h-6 left-[3px] top-[5px] absolute bg-sky-400" />
              </div>
              <div className="justify-center text-zinc-800 text-2xl font-normal font-['Avenir']">
                Sign up with Twitter
              </div>
            </div>
          </div>
        </div>
        <div className="w-[578px] inline-flex justify-start items-center gap-6">
          <div className="flex-1 h-0.5 bg-stone-500/25" />
          <div className="justify-center text-stone-500 text-2xl font-normal font-['Avenir']">
            OR
          </div>
          <div className="flex-1 h-0.5 bg-stone-500/25" />
        </div>
        <div className="flex flex-col justify-center items-center gap-10">
          <div className="text-center justify-start text-zinc-800 text-lg font-medium font-['Poppins']">
            Sign up with your email address
          </div>
          <div className="flex flex-col justify-start items-start gap-6">
            <div
              data-property-1="Generic Text field"
              className="w-[578px] flex flex-col justify-start items-start gap-1"
            >
              <div className="self-stretch h-7 relative">
                <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                  Profile name
                </div>
              </div>
              <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                <div className="left-[24px] top-[15px] absolute inline-flex justify-start items-center">
                  <div className="justify-start text-stone-500/60 text-base font-normal font-['Poppins']">
                    Enter your profile name
                  </div>
                </div>
              </div>
            </div>
            <div
              data-property-1="Generic Text field"
              className="w-[578px] flex flex-col justify-start items-start gap-1"
            >
              <div className="self-stretch h-7 relative">
                <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                  Email
                </div>
              </div>
              <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                <div className="left-[24px] top-[15px] absolute inline-flex justify-start items-center">
                  <div className="justify-start text-stone-500/60 text-base font-normal font-['Poppins']">
                    Enter your email address
                  </div>
                </div>
              </div>
            </div>
            <div
              data-property-1="Generic Text field"
              className="w-[578px] flex flex-col justify-start items-start gap-1"
            >
              <div className="self-stretch h-7 relative">
                <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                  Password
                </div>
                <div
                  data-property-1="Hide"
                  className="w-6 h-6 left-[496.14px] top-[3px] absolute overflow-hidden"
                >
                  <div className="w-4 h-4 left-[2.91px] top-[4.01px] absolute bg-stone-500/80" />
                  <div className="w-3 h-2.5 left-[9.80px] top-[8.75px] absolute bg-stone-500/80" />
                </div>
                <div className="left-[528.14px] top-0 absolute text-right justify-start text-stone-500/80 text-lg font-normal font-['Poppins']">
                  Hide
                </div>
              </div>
              <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                <div className="left-[24px] top-[15px] absolute inline-flex justify-start items-center">
                  <div className="justify-start text-stone-500/60 text-base font-normal font-['Poppins']">
                    Enter your password
                  </div>
                </div>
              </div>
              <div className="justify-center text-stone-500 text-sm font-normal font-['Poppins']">
                Use 8 or more characters with a mix of letters, numbers &amp;
                symbols
              </div>
            </div>
          </div>
          <div className="flex flex-col justify-start items-start gap-8">
            <div className="flex flex-col justify-start items-start gap-3">
              <div className="justify-start">
                <span className="text-neutral-900 text-base font-normal font-['Poppins']">
                  {"What's your gender? "}
                </span>
                <span className="text-stone-500 text-base font-normal font-['Poppins']">
                  (optional)
                </span>
              </div>
              <div className="inline-flex justify-start items-start gap-8">
                <div className="px-2 flex justify-center items-center gap-2">
                  <div
                    data-property-1="Radio button unchecked"
                    className="w-4 h-4 relative overflow-hidden"
                  >
                    <div className="w-4 h-4 left-0 top-0 absolute" />
                    <div className="w-3.5 h-3.5 left-[1.33px] top-[1.33px] absolute bg-black" />
                  </div>
                  <div className="justify-start text-neutral-900 text-base font-normal font-['Poppins']">
                    Female
                  </div>
                </div>
                <div className="px-2 flex justify-center items-center gap-2">
                  <div
                    data-property-1="Radio button unchecked"
                    className="w-4 h-4 relative overflow-hidden"
                  >
                    <div className="w-4 h-4 left-0 top-0 absolute" />
                    <div className="w-3.5 h-3.5 left-[1.33px] top-[1.33px] absolute bg-black" />
                  </div>
                  <div className="justify-start text-neutral-900 text-base font-normal font-['Poppins']">
                    Male
                  </div>
                </div>
                <div className="px-2 flex justify-center items-center gap-2">
                  <div
                    data-property-1="Radio button unchecked"
                    className="w-4 h-4 relative overflow-hidden"
                  >
                    <div className="w-4 h-4 left-0 top-0 absolute" />
                    <div className="w-3.5 h-3.5 left-[1.33px] top-[1.33px] absolute bg-black" />
                  </div>
                  <div className="justify-start text-neutral-900 text-base font-normal font-['Poppins']">
                    Non-binary
                  </div>
                </div>
              </div>
            </div>
            <div className="flex flex-col justify-start items-start gap-3">
              <div className="justify-start text-neutral-900 text-base font-normal font-['Poppins']">
                What's your date of borth?
              </div>
              <div className="inline-flex justify-start items-start gap-5">
                <div
                  data-property-1="Generic Text field"
                  className="w-44 inline-flex flex-col justify-start items-start gap-1"
                >
                  <div className="self-stretch h-7 relative">
                    <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                      Month
                    </div>
                  </div>
                  <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                    <div
                      data-property-1="Drop down line"
                      className="w-6 h-6 left-[132px] top-[16px] absolute overflow-hidden"
                    >
                      <div className="w-6 h-6 left-0 top-0 absolute" />
                      <div className="w-3 h-2 left-[6px] top-[8.59px] absolute bg-stone-500" />
                    </div>
                  </div>
                </div>
                <div
                  data-property-1="Generic Text field"
                  className="w-44 inline-flex flex-col justify-start items-start gap-1"
                >
                  <div className="self-stretch h-7 relative">
                    <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                      Date
                    </div>
                  </div>
                  <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                    <div
                      data-property-1="Drop down line"
                      className="w-6 h-6 left-[131px] top-[16px] absolute overflow-hidden"
                    >
                      <div className="w-6 h-6 left-0 top-0 absolute" />
                      <div className="w-3 h-2 left-[6px] top-[8.59px] absolute bg-stone-500" />
                    </div>
                  </div>
                </div>
                <div
                  data-property-1="Generic Text field"
                  className="w-44 inline-flex flex-col justify-start items-start gap-1"
                >
                  <div className="self-stretch h-7 relative">
                    <div className="left-0 top-0 absolute justify-start text-stone-500 text-base font-normal font-['Poppins']">
                      Year
                    </div>
                  </div>
                  <div className="self-stretch h-14 relative rounded-xl outline outline-1 outline-offset-[-1px] outline-stone-500/30 overflow-hidden">
                    <div
                      data-property-1="Drop down line"
                      className="w-6 h-6 left-[131px] top-[16px] absolute overflow-hidden"
                    >
                      <div className="w-6 h-6 left-0 top-0 absolute" />
                      <div className="w-3 h-2 left-[6px] top-[8.59px] absolute bg-stone-500" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="flex flex-col justify-start items-start gap-6">
            <div
              data-property-1="Check box 1 line"
              className="pr-2 py-2 inline-flex justify-start items-start gap-2"
            >
              <div
                data-property-1="Check box/check"
                className="w-6 h-6 relative overflow-hidden"
              >
                <div className="w-6 h-6 left-0 top-0 absolute" />
                <div className="w-4 h-4 left-[3px] top-[3px] absolute bg-neutral-900" />
              </div>
              <div className="justify-start text-zinc-800 text-base font-normal font-['Poppins']">
                Share my registration data with our content providers for
                <br />
                marketing purposes.
              </div>
            </div>
            <div className="pr-2 py-2 inline-flex justify-start items-start gap-2.5">
              <div className="justify-start">
                <span className="text-zinc-800 text-base font-normal font-['Poppins']">
                  By creating an account, you agree to the{" "}
                </span>
                <span className="text-neutral-900 text-base font-normal font-['Poppins'] underline">
                  Terms of use
                </span>
                <span className="text-stone-500 text-base font-normal font-['Poppins']">
                  {" "}
                </span>
                <span className="text-zinc-800 text-base font-normal font-['Poppins']">
                  and
                </span>
                <span className="text-stone-500 text-base font-normal font-['Poppins']">
                  {" "}
                </span>
                <span className="text-neutral-900 text-base font-normal font-['Poppins'] underline">
                  Privacy Policy.
                </span>
                <span className="text-stone-500 text-base font-normal font-['Poppins'] underline">
                  {" "}
                </span>
              </div>
            </div>
            <div className="w-96 h-16 relative bg-white rounded-2xl outline outline-1 outline-offset-[-1px] outline-zinc-800">
              <div className="left-[24px] top-[22px] absolute inline-flex justify-center items-center gap-2">
                <div
                  data-property-1="Check box/check"
                  className="w-4 h-4 relative overflow-hidden"
                >
                  <div className="w-4 h-4 left-0 top-0 absolute" />
                  <div className="w-3.5 h-3.5 left-[2.25px] top-[2.25px] absolute bg-green-600" />
                </div>
                <div className="text-center justify-center text-zinc-800 text-base font-light font-['Poppins']">
                  I'm not a robot
                </div>
              </div>
              <div className="w-12 h-12 left-[291px] top-[11px] absolute overflow-hidden">
                <div className="w-7 h-4 left-[10.91px] top-0 absolute bg-blue-800" />
                <div className="w-4 h-7 left-[7.62px] top-0 absolute bg-blue-500" />
                <div className="w-7 h-4 left-[7.62px] top-[16.16px] absolute bg-neutral-400" />
                <div className="w-12 h-2 left-0 top-[38.54px] absolute bg-neutral-400" />
              </div>
            </div>
          </div>
          <div className="flex flex-col justify-center items-center gap-4">
            <div className="w-[578px] h-16 relative opacity-25 bg-neutral-900 rounded-[40px] overflow-hidden">
              <div className="left-[247px] top-[15px] absolute inline-flex justify-center items-center gap-2">
                <div className="text-center justify-center text-white text-xl font-medium font-['Poppins']">
                  Sign up
                </div>
              </div>
            </div>
            <div className="p-0.5 inline-flex justify-start items-start gap-2.5">
              <div className="justify-start">
                <span className="text-zinc-800 text-base font-normal font-['Poppins']">
                  Already have an ccount?
                </span>
                <span className="text-stone-500 text-base font-normal font-['Poppins']">
                  {" "}
                </span>
                <span className="text-neutral-900 text-base font-normal font-['Poppins'] underline">
                  Log in{" "}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
